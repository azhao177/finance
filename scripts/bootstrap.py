"""Initialize a fresh local instance without logging or overwriting credentials."""
import secrets
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from werkzeug.security import generate_password_hash

app=create_app()
root=app.config['DATA_DIR']
if not (root/'password.hash').exists():
    password=secrets.token_urlsafe(32)
    with (root/'initial-password.txt').open('x') as output:
        output.write(password+'\n')
    with (root/'password.hash').open('x') as output:
        output.write(generate_password_hash(password))
    print('已初始化空账本。随机初始密码仅在私人数据目录 initial-password.txt 中。')
    print('本人首次使用前可运行 python app.py init 设置自己的密码。未生成演示账目。')
else:
    print('已有密码与数据，保持不变。')
