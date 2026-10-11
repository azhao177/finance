"""Check current tracked paths and proposed distributable paths, without reading history/data."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_ROOT={'.gitignore','README.md','PRODUCT.md','DESIGN.md','requirements.lock','app.py','ledger.py'}
ALLOWED_DIR={'assets':{'.css','.js'},'templates':{'.html'},'tests':{'.py'},'scripts':{'.py'},'docs':{'.md'},'examples':{'.csv'},'.impeccable':{'.json','.md'}}
def permitted(path):
    p=Path(path)
    if str(p) in ALLOWED_ROOT:return True
    if p.parts[0] in ALLOWED_DIR and p.suffix in ALLOWED_DIR[p.parts[0]]:
        return not any(x in ('private','uploads','exports','review','logs','backups','__pycache__') for x in p.parts)
    return False

tracked=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
proposed=[]
for name in ALLOWED_ROOT:
    if (ROOT/name).is_file():proposed.append(name)
for directory in ALLOWED_DIR:
    if (ROOT/directory).exists():
        proposed.extend(str(p.relative_to(ROOT)) for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
bad=[p for p in tracked if p and not permitted(p)]+[p for p in proposed if not permitted(p)]
if bad:
    print('拒绝发布：发现非代码／非虚构样例路径：',*sorted(set(bad)),sep='\n')
    sys.exit(1)
for path in proposed:
    if not permitted(path):continue
    # Frontend must remain local and contain no source maps or network endpoints.
    if Path(path).parts[0]=='assets':
        content=(ROOT/path).read_text()
        if 'sourceMappingURL' in content or 'https://' in content or 'http://' in content.replace('http://www.w3.org/2000/svg',''):
            raise SystemExit('前端资源含外部请求或源码映射，请人工检查：'+path)
print(f'通过：检查当前跟踪路径和 {len(proposed)} 个拟交付代码／文档／虚构样例文件。没有读取 Git 历史。')
print('发布真实资料前仍须本人检查文件内容；路径检查不能自动识别所有私人数据。')
