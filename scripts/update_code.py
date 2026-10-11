"""Update code from the owner's repository; never upload or replace private runtime data."""
import io
import os
from pathlib import Path
import secrets
import ssl
import stat
import tempfile
import urllib.request
from zipfile import ZipFile, ZIP_DEFLATED

ROOT_FILES={'.gitignore','README.md','PRODUCT.md','DESIGN.md','requirements.lock','app.py','ledger.py'}
DIRECTORIES={'assets':{'.css','.js'},'templates':{'.html'},'tests':{'.py'},'scripts':{'.py'},'docs':{'.md'},'examples':{'.csv'}}
REQUIRED={'app.py','ledger.py','assets/app.js','templates/index.html'}


def allowed(name):
    p=Path(name)
    return (name in ROOT_FILES or name=='.impeccable/design.json' or
            (len(p.parts)>=2 and p.parts[0] in DIRECTORIES and p.suffix in DIRECTORIES[p.parts[0]]))


def update(root, raw):
    root=Path(root).resolve()
    if not (root/'app.py').is_file() or not (root/'ledger.py').is_file():
        raise ValueError('请先 cd 进入原 finance-main 项目文件夹；不会在其他位置安装')
    contents={}
    with ZipFile(io.BytesIO(raw)) as archive:
        if sum(item.file_size for item in archive.infolist())>20*1024*1024:
            raise ValueError('代码压缩包过大，停止更新')
        prefixes=set()
        for item in archive.infolist():
            if item.is_dir():
                continue
            parts=Path(item.filename).parts
            if len(parts)<2 or '..' in parts or Path(item.filename).is_absolute() or stat.S_ISLNK(item.external_attr>>16):
                raise ValueError('压缩包路径不安全，停止更新')
            prefixes.add(parts[0])
            name=str(Path(*parts[1:]))
            if not allowed(name):
                raise ValueError('压缩包含未批准的非代码文件，停止更新：'+name)
            if name in contents:
                raise ValueError('压缩包存在重复文件，停止更新')
            target=root/name
            if not target.resolve().is_relative_to(root) or target.is_symlink() or (target.exists() and not target.is_file()):
                raise ValueError('目标代码路径异常，停止更新：'+name)
            contents[name]=archive.read(item)
        if len(prefixes)!=1 or not REQUIRED.issubset(contents):
            raise ValueError('压缩包不是完整 finance 项目，停止更新')
    backup_dir=root/'.runtime'/'code-backups'
    backup_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    backup=backup_dir/('code-'+secrets.token_hex(6)+'.zip')
    prior={name:(root/name).read_bytes() if (root/name).exists() else None for name in contents}
    with ZipFile(backup,'x',ZIP_DEFLATED) as archive:
        for name,content in prior.items():
            if content is not None:
                archive.writestr(name,content)
    written=[]
    try:
        for name,content in contents.items():
            target=root/name
            target.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as file:
                file.write(content)
                temporary=Path(file.name)
            try:
                os.replace(temporary,target)
            finally:
                temporary.unlink(missing_ok=True)
            written.append(name)
    except Exception:
        for name in reversed(written):
            target=root/name
            if prior[name] is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(prior[name])
        raise
    return len(contents),backup


def main():
    os.umask(0o077)
    root=Path.cwd()
    if not (root/'app.py').is_file() or not (root/'ledger.py').is_file():
        raise SystemExit('请先 cd 进入原 finance-main 文件夹，再运行更新；现有文件未修改。')
    # macOS python.org installers may require CA initialization. Reuse pip's verified CA bundle.
    try:
        from pip._vendor import certifi
        context=ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context=ssl.create_default_context()
    url='https://codeload.github.com/azhao177/finance/zip/refs/heads/main'
    with urllib.request.urlopen(url,context=context,timeout=60) as response:
        raw=response.read(10*1024*1024+1)
    if len(raw)>10*1024*1024:
        raise SystemExit('下载文件过大，停止更新；现有文件未修改。')
    count,backup=update(root,raw)
    print(f'已更新 {count} 个代码／文档文件。数据库、账单、密码和 .venv 均保留。')
    print('旧代码备份：'+str(backup))
    print('现在运行：.venv/bin/python app.py serve --host 127.0.0.1 --port 8000')


if __name__=='__main__':
    main()
