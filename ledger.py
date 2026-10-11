"""Exact ledger operations. No external network or merchant inference."""
import calendar
import csv
import hashlib
import io
import json
import re
import sqlite3
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import load_workbook, Workbook
from pypdf import PdfReader

KINDS = {'income': '收入', 'expense': '消费', 'transfer': '转账', 'payment': '还款',
         'refund': '退款／返现', 'reimbursement': '分摊／归还借款', 'withdrawal': '取现'}
CATEGORIES = {
    '房子': ['房贷', '管理费', '水电', '宽带', '房屋保险', '地税'],
    '车': ['车贷', '加油', '停车', '车保险', '维修'],
    '上班': ['通勤', '工作餐', '工作服', '工作活动'],
    '运动': ['健身会费', '课程', '场地', '运动装备', '营养补充品'],
    '学习': ['AI 工具', '课程', '书籍'], '旅行': ['机票', '酒店', '交通', '门票／活动票', '旅游吃喝'],
    '饮食': ['餐厅', '咖啡', '外卖', '超市'], '购物': ['其他'], '玩／娱乐': ['其他'],
    '娱乐与订阅': ['订阅'], '健康': ['其他'], '家具': ['其他'], '待确认': ['待确认'],
}
COLORS = ['#aedbc8', '#bed4ed', '#f3cbb8', '#e8b9d1', '#cbbfe8', '#b7ddd9',
          '#d9ddb7', '#c8d7e5', '#edd4bd', '#d9c6db', '#c5d6bd', '#d7cfeb', '#d3dce0']
HEADERS = ['transaction_date', 'posting_date', 'description', 'amount', 'currency', 'type',
           'status', 'external_id', 'original_amount', 'original_currency', 'category', 'subcategory', 'notes']


def connect(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def init_db(path):
    with connect(path) as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL, currency TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS categories(name TEXT PRIMARY KEY, children TEXT NOT NULL, color TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
            digest TEXT NOT NULL, name TEXT NOT NULL, ext TEXT NOT NULL, coverage_start TEXT, coverage_end TEXT,
            UNIQUE(account_id,digest));
        CREATE TABLE IF NOT EXISTS transactions(id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
            transaction_date TEXT NOT NULL, posting_date TEXT, description TEXT NOT NULL, amount INTEGER NOT NULL,
            currency TEXT NOT NULL, type TEXT NOT NULL, status TEXT NOT NULL, external_id TEXT,
            original_amount INTEGER, original_currency TEXT, category TEXT NOT NULL, subcategory TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '', manual INTEGER NOT NULL DEFAULT 0, fingerprint TEXT NOT NULL,
            occurrence INTEGER NOT NULL, UNIQUE(account_id,fingerprint,occurrence));
        CREATE UNIQUE INDEX IF NOT EXISTS bank_identity ON transactions(account_id,external_id)
            WHERE external_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS sources(transaction_id TEXT NOT NULL REFERENCES transactions(id),
            file_id TEXT NOT NULL REFERENCES files(id), line INTEGER NOT NULL, page INTEGER,
            PRIMARY KEY(transaction_id,file_id,line));
        CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY, description TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL, subcategory TEXT NOT NULL, type TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS aliases(account_id TEXT NOT NULL, fingerprint TEXT NOT NULL, occurrence INTEGER NOT NULL,
            transaction_id TEXT NOT NULL REFERENCES transactions(id), PRIMARY KEY(account_id,fingerprint,occurrence));
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, expires INTEGER NOT NULL);
        ''')
        for i, (name, children) in enumerate(CATEGORIES.items()):
            db.execute('INSERT OR IGNORE INTO categories VALUES(?,?,?)', (name, json.dumps(children), COLORS[i]))


def iso(value, required=True):
    if value is None or value == '':
        if required:
            raise ValueError('缺少交易日期；不能猜测日期')
        return None
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    value = str(value).strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('日期须为 YYYY-MM-DD，含完整年份')
    return date.fromisoformat(value).isoformat()


def cents(value):
    try:
        num = Decimal(str(value).strip())
        if not num.is_finite() or num != num.quantize(Decimal('.01')) or abs(num) > Decimal('9999999999.99'):
            raise ValueError('金额须为有限的两位小数，且不超过 99 亿')
        return int(num * 100)
    except (InvalidOperation, TypeError):
        raise ValueError('金额须为明确数字，不接受货币符号、逗号或公式') from None


def text(value, limit=2000):
    return str(value or '').strip()[:limit]


def normalize(row, currency):
    kind = text(row.get('type'))
    if kind not in KINDS:
        raise ValueError('type 必须明确指定 income / expense / transfer / payment / refund / reimbursement / withdrawal')
    status = text(row.get('status')) or 'posted'
    if status not in ('posted', 'pending'):
        raise ValueError('status 必须是 posted 或 pending')
    amount = cents(row.get('amount'))
    if amount < 0:
        raise ValueError('amount 使用正数，收支方向由 type 明确指定；不可猜测正负含义')
    cur = text(row.get('currency')) or currency
    if cur != currency:
        raise ValueError('currency 必须是该账户的账单本币；原币使用 original_currency')
    desc = text(row.get('description'))
    if not desc:
        raise ValueError('缺少原始描述')
    orig = row.get('original_amount')
    orig_cur = text(row.get('original_currency'))
    if bool(orig is not None and orig != '') != bool(orig_cur):
        raise ValueError('原币金额与币种须同时提供')
    if orig_cur and not re.fullmatch('[A-Z]{3}', orig_cur):
        raise ValueError('原币币种须为三位大写字母')
    return dict(transaction_date=iso(row.get('transaction_date')), posting_date=iso(row.get('posting_date'), False),
                description=desc, amount=amount, currency=cur, type=kind, status=status,
                external_id=text(row.get('external_id'), 200) or None,
                original_amount=cents(orig) if orig_cur else None, original_currency=orig_cur or None,
                category=text(row.get('category')) or '待确认', subcategory=text(row.get('subcategory')) or '待确认',
                notes=text(row.get('notes')))


def fingerprint(row):
    # Keep a conservative literal description; no fuzzy merchant/date matching.
    return hashlib.sha256(json.dumps([row['transaction_date'], row['description'], row['amount'], row['currency'], row.get('external_id')],
                                     ensure_ascii=False).encode()).hexdigest()


def parse_file(data, ext):
    """Only explicit canonical columns; unknown PDF layouts fail closed."""
    if ext == '.csv':
        content = data.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames or not set(HEADERS[:6]).issubset(reader.fieldnames):
            raise ValueError('CSV 缺少标准列，请按导入说明映射列名')
        return [(r, reader.line_num, None) for r in reader]
    if ext == '.xlsx':
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=False)
        rows = []
        # One sheet per upload: avoids silently omitting unknown worksheets.
        if len(wb.worksheets) != 1:
            raise ValueError('导入 Excel 须只有一个交易 sheet；年度导出是报表，不直接回导')
        ws = wb.worksheets[0]
        iterator = ws.iter_rows(values_only=True)
        headers = list(next(iterator, ()))
        if not set(HEADERS[:6]).issubset(headers):
            raise ValueError('Excel 缺少标准列')
        for i, values in enumerate(iterator, 2):
            if all(v is None for v in values):
                continue
            if any(isinstance(v, str) and v.startswith('=') for v in values):
                raise ValueError(f'第 {i} 行含公式；请导入已经核对的数值')
            rows.append((dict(zip(headers, values)), i, None))
        return rows
    if ext == '.pdf':
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError('加密 PDF 请本人本地解密后导入，不保存解密密码')
        rows = []
        for p, page in enumerate(reader.pages, 1):
            lines = (page.extract_text() or '').splitlines()
            headers = None
            for i, line in enumerate(lines, 1):
                if line.startswith('transaction_date|'):
                    headers = line.split('|')
                    if not set(HEADERS[:6]).issubset(headers):
                        raise ValueError('PDF 标准表头不完整')
                elif headers and line.strip():
                    values = line.split('|')
                    if len(values) != len(headers):
                        raise ValueError(f'PDF 第 {p} 页第 {i} 行换行或列数异常；请使用结构化 CSV')
                    rows.append((dict(zip(headers, values)), i, p))
        if not rows:
            raise ValueError('不支持该 PDF 版式或无文本层。请本地转换成标准 CSV 并核对；不会启用外部 OCR')
        return rows
    raise ValueError('仅支持 .csv、.xlsx、含文本标准表格的 .pdf；旧 .xls 请本地另存 .xlsx')


def validate_category(db, row):
    cat = db.execute('SELECT children FROM categories WHERE name=?', (row['category'],)).fetchone()
    if not cat or row['subcategory'] not in json.loads(cat[0]):
        raise ValueError('分类组合不存在；请先在分类管理中添加')


def preview(db, data, ext, account):
    rows = parse_file(data, ext)
    if len(rows) > 20000:
        raise ValueError('单文件最多 20,000 笔，请拆分文件')
    result, counts = [], Counter()
    for raw, line, page in rows:
        try:
            row = normalize(raw, account['currency'])
            validate_category(db, row)
            fp = fingerprint(row)
            counts[fp] += 1
            row.update(line=line, page=page, fingerprint=fp, occurrence=counts[fp])
            existing = None
            if row['external_id']:
                existing = db.execute('SELECT * FROM transactions WHERE account_id=? AND external_id=?',
                                      (account['id'], row['external_id'])).fetchone()
            if not existing:
                existing = db.execute('SELECT * FROM transactions WHERE account_id=? AND fingerprint=? AND occurrence=?',
                                      (account['id'], fp, counts[fp])).fetchone()
            if not existing and row['external_id']:
                legacy_fp = fingerprint({**row, 'external_id': None})
                existing = db.execute('SELECT * FROM transactions WHERE account_id=? AND fingerprint=? AND occurrence=? AND external_id IS NULL',
                                      (account['id'], legacy_fp, counts[fp])).fetchone()
            if not existing:
                existing = db.execute('SELECT t.* FROM aliases a JOIN transactions t ON t.id=a.transaction_id WHERE a.account_id=? AND a.fingerprint=? AND a.occurrence=?',
                                      (account['id'], fp, counts[fp])).fetchone()
            row['match_id'] = existing['id'] if existing else None
            if existing:
                row['action'] = 'update' if existing['status'] == 'pending' and row['status'] == 'posted' else 'duplicate'
                if existing['amount'] != row['amount'] or existing['transaction_date'] != row['transaction_date']:
                    row['action'] = 'review'
            else:
                row['action'] = 'new'
            # Potential pending settlement with changed dates/description requires explicit ID selection.
            row['candidates'] = [dict(r) for r in db.execute(
                "SELECT id,transaction_date,description FROM transactions WHERE account_id=? AND status='pending' AND amount=? AND currency=?",
                (account['id'], row['amount'], row['currency']))] if not existing and row['status'] == 'posted' else []
            result.append(row)
        except ValueError as error:
            raise ValueError(f'第 {line} 行：{error}') from None
    if not result:
        raise ValueError('文件没有交易行')
    return result


def commit_import(db, rows, account, file_id, decisions):
    added = updated = duplicates = 0
    used = set()
    for i, original in enumerate(rows):
        row = dict(original)
        decision = decisions.get(str(i), {})
        if decision.get('skip'):
            continue
        # Corrections are limited to explicit financial type / category, never silent date/amount changes.
        for field in ('category', 'subcategory', 'type'):
            if field in decision:
                row[field] = text(decision[field])
        if row['type'] not in KINDS:
            raise ValueError('交易类型不合法')
        validate_category(db, row)
        target = decision.get('match_id') or row.get('match_id')
        if decision.get('match_id') and decision['match_id'] != row.get('match_id') and decision['match_id'] not in {c['id'] for c in row['candidates']}:
            raise ValueError('只能匹配预览中列出的临时记录')
        if not target and row['external_id']:
            same = db.execute('SELECT * FROM transactions WHERE account_id=? AND external_id=?', (account['id'],row['external_id'])).fetchone()
            if same:
                if same['amount'] != row['amount'] or same['transaction_date'] != row['transaction_date'] or same['description'] != row['description']:
                    raise ValueError('同一文件中银行 ID 对应冲突交易，请核对文件')
                target = same['id']
        if row['action'] == 'review' and not decision.get('confirm'):
            raise ValueError('相同银行 ID 的日期／金额变动须明确确认')
        if row['candidates'] and not target and not decision.get('confirm'):
            raise ValueError('疑似临时记录须选择匹配 ID 或确认是一笔新交易')
        if target:
            old = db.execute('SELECT * FROM transactions WHERE id=? AND account_id=?', (target, account['id'])).fetchone()
            if not old or (target in used and decision.get('match_id')):
                raise ValueError('匹配记录不存在或被多行重复使用')
            used.add(target)
            if old['status'] == 'pending' and row['status'] == 'posted' or row['action'] == 'review':
                db.execute('''UPDATE transactions SET transaction_date=?,posting_date=?,status=?,external_id=COALESCE(external_id,?),
                    description=?,amount=?,original_amount=?,original_currency=? WHERE id=?''',
                    (row['transaction_date'], row['posting_date'], row['status'], row['external_id'],
                     row['description'], row['amount'], row['original_amount'], row['original_currency'], target))
                updated += 1
            else:
                # Refresh posting date without regressing settled records to pending.
                if row['status'] == 'posted':
                    db.execute('UPDATE transactions SET posting_date=COALESCE(?,posting_date),external_id=COALESCE(external_id,?) WHERE id=?', (row['posting_date'], row['external_id'], target))
                duplicates += 1
        else:
            target = str(uuid.uuid4())
            rule = db.execute('SELECT * FROM rules WHERE description=?', (row['description'],)).fetchone()
            manual = bool(decision)
            if rule and not manual:
                for field in ('category', 'subcategory', 'type'):
                    row[field] = rule[field]
            fields = ['transaction_date','posting_date','description','amount','currency','type','status','external_id',
                      'original_amount','original_currency','category','subcategory','notes','fingerprint','occurrence']
            db.execute('INSERT INTO transactions(id,account_id,manual,' + ','.join(fields) + ') VALUES(' + ','.join('?' for _ in range(18)) + ')',
                       [target, account['id'], int(manual)] + [row[f] for f in fields])
            added += 1
        db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?)', (target, file_id, row['line'], row['page']))
        db.execute('INSERT OR IGNORE INTO aliases VALUES(?,?,?,?)', (account['id'],row['fingerprint'],row['occurrence'],target))
    if sum(r[0] for r in db.execute('SELECT amount FROM transactions')) > 9007199254740991:
        raise ValueError('账本累计金额超过浏览器精确整数上限，导入已回滚')
    return dict(added=added, updated=updated, duplicates=duplicates)


def get_transactions(db):
    rows = [dict(r) for r in db.execute('SELECT t.*,a.name account FROM transactions t JOIN accounts a ON a.id=t.account_id ORDER BY transaction_date DESC,id')]
    for row in rows:
        row['sources'] = [dict(r) for r in db.execute('SELECT s.file_id,s.line,s.page,f.name FROM sources s JOIN files f ON f.id=s.file_id WHERE transaction_id=?', (row['id'],))]
    return rows


def summarize(rows):
    totals = {k: 0 for k in KINDS}
    totals['pending'] = 0
    categories, subcategories = defaultdict(int), defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r['status'] == 'pending':
            totals['pending'] += r['amount']
            continue
        totals[r['type']] += r['amount']
        if r['type'] == 'expense':
            categories[r['category']] += r['amount']
            subcategories[r['category']][r['subcategory']] += r['amount']
    totals['balance'] = totals['income'] - totals['expense']
    return dict(totals=totals, categories=dict(sorted(categories.items(), key=lambda kv: -kv[1])),
                subcategories={k: dict(v) for k,v in subcategories.items()})


def export_excel(db):
    wb = Workbook()
    wb.remove(wb.active)
    rows = get_transactions(db)
    years = sorted({r['transaction_date'][:4] for r in rows})
    if not years:
        wb.create_sheet('无记录').append(['暂无已导入交易'])
    for year in years:
        ws = wb.create_sheet(year)
        ws.append(['ID','交易日期','入账日期','账户','本币','金额','类型','状态','大类','二级分类','备注','原始描述','来源','原币','原币金额'])
        for account in db.execute('SELECT * FROM accounts ORDER BY name'):
            for r in rows:
                if r['account_id'] != account['id'] or not r['transaction_date'].startswith(year):
                    continue
                values = [r['id'],r['transaction_date'],r['posting_date'],r['account'],r['currency'],Decimal(r['amount'])/100,
                          r['type'],r['status'],r['category'],r['subcategory'],r['notes'],r['description'],
                          '; '.join(f"{s['file_id']}:{s['name']} page={s['page']} line={s['line']}" for s in r['sources']),
                          r['original_currency'],Decimal(r['original_amount'])/100 if r['original_amount'] is not None else None]
                ws.append(values)
                for cell in ws[ws.max_row]:
                    # Untrusted text is always stored as text, never a spreadsheet formula.
                    if isinstance(cell.value, str):
                        cell.data_type = 's'
                ws.cell(ws.max_row, 6).number_format = '0.00'
                ws.cell(ws.max_row, 15).number_format = '0.00'
        end = max(ws.max_row, 2)
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = f'A1:O{end}'
        ws.column_dimensions['L'].width = 40
        for col in 'ABCDEFGHIJKMNO':
            ws.column_dimensions[col].width = 20
        # Same yearly sheet; currency-aware formulas trace directly to transaction rows.
        ws['Q1'],ws['R1'],ws['S1'],ws['T1'] = '币种／分类', '收入', '消费', '结余／占比'
        at = 2
        for currency in sorted({r['currency'] for r in rows if r['transaction_date'].startswith(year)}):
            ws.cell(at,17,currency)
            for col,kind in [(18,'income'),(19,'expense')]:
                ws.cell(at,col,f'=SUMIFS(F2:F{end},E2:E{end},Q{at},G2:G{end},"{kind}",H2:H{end},"posted")')
            ws.cell(at,20,f'=R{at}-S{at}')
            summary_row = at
            at += 1
            for cat in db.execute('SELECT name FROM categories'):
                ws.cell(at,17,cat['name'])
                ws.cell(at,19,f'=SUMIFS(F2:F{end},E2:E{end},Q{summary_row},G2:G{end},"expense",H2:H{end},"posted",I2:I{end},Q{at})')
                ws.cell(at,20,f'=IFERROR(S{at}/S{summary_row},0)').number_format = '0.00%'
                at += 1
        for col in 'QRST':
            ws.column_dimensions[col].width = 20
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
