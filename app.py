"""Single-owner local finance app. All ledger routes authenticate on the server."""
import argparse
import getpass
import hashlib
import io
import json
import os
import secrets
import time
from datetime import timedelta
from pathlib import Path
import uuid

from flask import Flask, jsonify, request, session, redirect, render_template, send_file, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
import ledger

ROOT = Path(__file__).resolve().parent


def create_app(data_dir=None, testing=False):
    os.umask(0o077)
    app = Flask(__name__, static_folder=None)
    data = Path(data_dir or os.environ.get('LEDGER_DATA_DIR', ROOT / '.runtime')).resolve()
    if data == ROOT / 'assets' or ROOT / 'assets' in data.parents:
        raise RuntimeError('私人数据目录不能位于前端资源目录')
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    for directory in ('files','staging'):
        (data / directory).mkdir(exist_ok=True, mode=0o700)
    keyfile = data / 'session.key'
    if not keyfile.exists():
        with keyfile.open('xb') as f:
            f.write(secrets.token_bytes(32))
    app.config.update(SECRET_KEY=keyfile.read_bytes(), MAX_CONTENT_LENGTH=20*1024*1024, TESTING=testing,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                      SESSION_COOKIE_SECURE=os.environ.get('LEDGER_HTTPS') == '1',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8), DATA_DIR=data, DB=str(data/'ledger.sqlite3'))
    ledger.init_db(app.config['DB'])
    attempts = {}

    def db():
        return ledger.connect(app.config['DB'])

    @app.before_request
    def protect():
        if request.path in ('/assets/style.css','/favicon.ico'):
            return
        if request.path == '/login':
            return
        with db() as conn:
            active = conn.execute('SELECT 1 FROM sessions WHERE token=? AND expires>?',
                                  (session.get('token',''),int(time.time()))).fetchone()
        if not active:
            if session.get('token'):
                session.clear()
            if request.path.startswith('/api/') or request.path.startswith('/files/'):
                return jsonify(error='请先登录'), 401
            return redirect('/login')
        if request.method in ('POST','PATCH','DELETE'):
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf','')
            if not secrets.compare_digest(token, session.get('csrf','')):
                return jsonify(error='请求验证失败，请刷新后重试'),403

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(Exception)
    def errors(error):
        if isinstance(error,(ValueError, UnicodeError)):
            return jsonify(error=str(error)),400
        if isinstance(error,HTTPException):
            return jsonify(error='文件过大（最多 20MB）' if error.code == 413 else '请求无法完成'),error.code
        # Never echo statement content or stack locals into logs/API responses.
        if app.testing:
            raise error
        return jsonify(error='处理失败，未完成的导入不会入账。请核对格式并重试'),500

    @app.route('/login',methods=['GET','POST'])
    def login():
        error = None
        if request.method == 'POST':
            if not secrets.compare_digest(request.form.get('csrf',''),session.get('login_csrf','!')):
                return render_template('login.html',error='页面已过期，请刷新重试',csrf=session.get('login_csrf','')),403
            address = request.remote_addr
            now = time.time()
            prior = [stamp for stamp in attempts.get(address,[]) if now-stamp < 600]
            attempts[address] = prior
            if len(prior) >= 10:
                return render_template('login.html',error='尝试过多，请 10 分钟后重试',csrf=session['login_csrf']),429
            attempts[address].append(now)
            password_file = data/'password.hash'
            if password_file.exists() and check_password_hash(password_file.read_text(), request.form.get('password','')):
                session.clear()
                session.permanent = True
                session['token'],session['csrf'] = secrets.token_urlsafe(32),secrets.token_urlsafe(32)
                with db() as conn:
                    conn.execute('DELETE FROM sessions WHERE expires<?',(int(now),))
                    conn.execute('INSERT INTO sessions VALUES(?,?)',(session['token'],int(now)+8*3600))
                attempts.pop(address,None)
                return redirect('/')
            error = '密码不正确，或尚未执行本地密码初始化'
        session['login_csrf'] = secrets.token_urlsafe(32)
        return render_template('login.html',error=error,csrf=session['login_csrf'])

    @app.post('/logout')
    def logout():
        with db() as conn:
            conn.execute('DELETE FROM sessions WHERE token=?',(session.get('token'),))
        session.clear()
        return redirect('/login')

    @app.get('/')
    def home():
        return render_template('index.html',csrf=session['csrf'])

    @app.get('/assets/<name>')
    def assets(name):
        if name not in ('style.css','app.js'):
            return jsonify(error='不存在'),404
        return send_from_directory(ROOT/'assets',name)

    @app.get('/favicon.ico')
    def favicon():
        return '',204

    @app.get('/api/data')
    def get_data():
        with db() as conn:
            return jsonify(accounts=[dict(r) for r in conn.execute('SELECT * FROM accounts ORDER BY name')],
                           transactions=ledger.get_transactions(conn),types=ledger.KINDS,
                           categories=[dict(name=r['name'],children=json.loads(r['children']),color=r['color']) for r in conn.execute('SELECT * FROM categories')],
                           files=[dict(r) for r in conn.execute('SELECT * FROM files')],
                           rules=[dict(r) for r in conn.execute('SELECT * FROM rules')])

    @app.post('/api/accounts')
    def add_account():
        row=request.get_json()
        name=ledger.text(row.get('name'),100)
        kind=row.get('kind')
        currency=row.get('currency','CAD')
        if not name or kind not in ('chequing','debit','savings','credit','cash','investment') or not ledger.re.fullmatch('[A-Z]{3}',currency):
            raise ValueError('账户名称、类型或币种不合法')
        with db() as conn:
            if conn.execute('SELECT 1 FROM accounts WHERE name=?',(name,)).fetchone():
                raise ValueError('账户名称已存在，请保留每张卡的独立标识')
            conn.execute('INSERT INTO accounts VALUES(?,?,?,?)',(str(uuid.uuid4()),name,kind,currency))
        return jsonify(ok=True)

    @app.post('/api/categories')
    def categories():
        row=request.get_json()
        name=ledger.text(row.get('name'),60)
        child=ledger.text(row.get('child'),60)
        if not name or not child:
            raise ValueError('请填写大类和二级分类')
        with db() as conn:
            old=conn.execute('SELECT * FROM categories WHERE name=?',(name,)).fetchone()
            if old:
                children=json.loads(old['children'])
                if child not in children:
                    children.append(child)
                conn.execute('UPDATE categories SET children=? WHERE name=?',(json.dumps(children),name))
            else:
                index=conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0]
                conn.execute('INSERT INTO categories VALUES(?,?,?)',(name,json.dumps([child]),ledger.COLORS[index%len(ledger.COLORS)]))
        return jsonify(ok=True)

    @app.patch('/api/transactions/<tid>')
    def edit_transaction(tid):
        row=request.get_json()
        with db() as conn:
            old=conn.execute('SELECT * FROM transactions WHERE id=?',(tid,)).fetchone()
            if not old:
                return jsonify(error='交易不存在'),404
            row={key: ledger.text(row.get(key,old[key])) for key in ('category','subcategory','notes','type')}
            ledger.validate_category(conn,row)
            if row['type'] not in ledger.KINDS:
                raise ValueError('类型不合法')
            conn.execute('UPDATE transactions SET category=?,subcategory=?,notes=?,type=?,manual=1 WHERE id=?',
                         (row['category'],row['subcategory'],row['notes'],row['type'],tid))
            if request.json.get('future_rule') is True:
                conn.execute('INSERT INTO rules VALUES(?,?,?,?,?) ON CONFLICT(description) DO UPDATE SET category=excluded.category,subcategory=excluded.subcategory,type=excluded.type',
                             (str(uuid.uuid4()),old['description'],row['category'],row['subcategory'],row['type']))
        return jsonify(ok=True)

    @app.delete('/api/rules/<rid>')
    def remove_rule(rid):
        with db() as conn:
            conn.execute('DELETE FROM rules WHERE id=?',(rid,))
        return jsonify(ok=True)

    @app.post('/api/import/preview')
    def import_preview():
        for prior in (data/'staging').glob('*.json'):
            if time.time()-prior.stat().st_mtime>3600:
                prior.with_suffix('.bin').unlink(missing_ok=True)
                prior.unlink(missing_ok=True)
        file=request.files.get('file')
        if not file:
            raise ValueError('请选择文件')
        account_id=request.form.get('account_id')
        with db() as conn:
            account=conn.execute('SELECT * FROM accounts WHERE id=?',(account_id,)).fetchone()
            if not account:
                raise ValueError('请先创建并选择账户')
            filename=Path(file.filename.replace('\\','/')).name[:150]
            ext=Path(filename).suffix.lower()
            raw=file.read()
            digest=hashlib.sha256(raw).hexdigest()
            prior=conn.execute('SELECT id FROM files WHERE account_id=? AND digest=?',(account_id,digest)).fetchone()
            if prior:
                return jsonify(duplicate_file=True,rows=[],file_id=prior['id'])
            rows=ledger.preview(conn,raw,ext,account)
        start=ledger.iso(request.form.get('coverage_start'),False)
        end=ledger.iso(request.form.get('coverage_end'),False)
        if bool(start)!=bool(end) or (start and start>end):
            raise ValueError('覆盖开始和结束须同时填写，并按日期先后排列')
        token=str(uuid.uuid4())
        (data/'staging'/f'{token}.bin').write_bytes(raw)
        metadata=dict(account_id=account_id,name=filename,ext=ext,digest=digest,coverage_start=start,coverage_end=end,
                      created=time.time(),session_token=session['token'])
        (data/'staging'/f'{token}.json').write_text(json.dumps(metadata))
        return jsonify(token=token,rows=rows,summary=ledger.summarize(rows),warning='相同日期、原始描述、金额且无银行 ID 的交易按出现次数匹配；重叠文件不能区分巧合的同额消费，请逐行核对。')

    @app.post('/api/import/commit')
    def import_commit():
        args=request.get_json()
        token=args.get('token','')
        try:
            token=str(uuid.UUID(token))
        except ValueError:
            raise ValueError('导入预览 ID 不合法') from None
        metadata_path=data/'staging'/f'{token}.json'
        if not metadata_path.exists():
            raise ValueError('预览已失效，请重新上传')
        metadata=json.loads(metadata_path.read_text())
        if metadata['session_token'] != session['token'] or time.time()-metadata['created']>3600:
            raise ValueError('预览已过期，请重新上传')
        with db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT id FROM files WHERE account_id=? AND digest=?',(metadata['account_id'],metadata['digest'])).fetchone():
                return jsonify(added=0,updated=0,duplicates=0,duplicate_file=True)
            account=conn.execute('SELECT * FROM accounts WHERE id=?',(metadata['account_id'],)).fetchone()
            raw=(data/'staging'/f'{token}.bin').read_bytes()
            rows=ledger.preview(conn,raw,metadata['ext'],account)
            fid=str(uuid.uuid4())
            conn.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?)',
                         (fid,account['id'],metadata['digest'],metadata['name'],metadata['ext'],metadata['coverage_start'],metadata['coverage_end']))
            result=ledger.commit_import(conn,rows,account,fid,args.get('decisions',{}))
            (data/'files'/fid).write_bytes(raw)
        metadata_path.unlink(missing_ok=True)
        (data/'staging'/f'{token}.bin').unlink(missing_ok=True)
        return jsonify(**result)

    @app.get('/files/<fid>')
    def file_download(fid):
        with db() as conn:
            file=conn.execute('SELECT * FROM files WHERE id=?',(fid,)).fetchone()
        if not file:
            return jsonify(error='文件不存在'),404
        return send_file(data/'files'/fid,as_attachment=True,download_name=file['name'],mimetype='application/octet-stream')

    @app.get('/api/export.xlsx')
    def export():
        with db() as conn:
            output=ledger.export_excel(conn)
        return send_file(output,as_attachment=True,download_name='private-ledger.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    return app


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['init','serve'])
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    app=create_app()
    if args.command=='init':
        password=getpass.getpass('设置本实例密码（至少 12 字符）：')
        confirm=getpass.getpass('再次输入密码：')
        if password!=confirm or len(password)<12:
            raise SystemExit('密码不一致或不足 12 字符')
        (app.config['DATA_DIR']/'password.hash').write_text(generate_password_hash(password))
        (app.config['DATA_DIR']/'initial-password.txt').unlink(missing_ok=True)
        with ledger.connect(app.config['DB']) as db:
            db.execute('DELETE FROM sessions')
        print('密码已设置；现有登录已撤销。数据保留。')
    else:
        if not (app.config['DATA_DIR']/'password.hash').exists():
            raise SystemExit('先执行 python app.py init；不会提供默认密码。')
        from waitress import serve
        serve(app,host=args.host,port=args.port,threads=4)


if __name__=='__main__':
    main()
