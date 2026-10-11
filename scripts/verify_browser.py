"""End-to-end checks against an isolated, entirely fictional temporary instance."""
import argparse
from pathlib import Path
import secrets
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import create_app
from werkzeug.security import generate_password_hash
from waitress import create_server
from playwright.sync_api import sync_playwright, expect

parser=argparse.ArgumentParser()
parser.add_argument('--chromium',default='/usr/bin/chromium')
parser.add_argument('--screenshots',type=Path)
args=parser.parse_args()

with tempfile.TemporaryDirectory(prefix='fictional-ledger-') as directory:
    root=Path(directory)
    app=create_app(root,testing=True)
    password=secrets.token_urlsafe(32)
    (root/'password.hash').write_text(generate_password_hash(password))
    server=create_server(app,host='127.0.0.1',port=0)
    thread=threading.Thread(target=server.run,daemon=True)
    thread.start()
    output=args.screenshots or root/'screenshots'
    output.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.effective_port}/login')
            page.locator('#password').fill(password)
            page.get_by_role('button',name='登录账本').click()
            page.get_by_role('button',name='账户与分类').click()
            page.locator('#account-form input[name=name]').fill('虚构信用卡 A')
            page.locator('#account-form button').click()
            expect(page.locator('#settings-accounts')).to_contain_text('虚构信用卡 A')
            page.locator('#settings-dialog [data-close]').click()
            page.get_by_role('button',name='导入账单',exact=True).click()
            page.locator('input[type=file]').set_input_files(str(ROOT/'examples/demo.csv'))
            page.get_by_role('button',name='解析并预览').click()
            page.get_by_role('button',name='确认核对并追加到账本').click()
            expect(page.locator('#expense')).to_contain_text('1,546.43')
            assert page.locator('#period').input_value()=='2026-02'
            assert '4,250.00' in page.locator('#income').inner_text()
            assert '2,703.57' in page.locator('#balance').inner_text()
            page.screenshot(path=str(output/'desktop.png'),full_page=True)
            page.locator('#category-list button').filter(has_text='饮食').click()
            page.locator('#drill button').filter(has_text='超市').click()
            assert page.locator('#transaction-list button').count()==1
            page.locator('#transaction-list button').click()
            page.locator('#detail-content textarea').fill('虚构测试备注')
            page.get_by_role('button',name='保存修改').click()
            expect(page.locator('#detail-dialog')).not_to_be_visible()
            page.get_by_role('button',name='显示全部明细').click()
            page.locator('#yearly').click()
            assert '2026-02-28' in page.locator('#range-title').inner_text()
            assert page.locator('#trend .trend-cell').count()==12
            assert '10 月' in page.locator('#trend').inner_text()
            page.screenshot(path=str(output/'annual.png'),full_page=True)
            page.locator('#monthly').click()
            for width in [1440,390,320]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                if width!=1440:
                    page.screenshot(path=str(output/f'mobile-{width}.png'),full_page=True)
                    page.locator('#transaction-list button').first.click()
                    assert page.locator('#detail-dialog').is_visible()
                    assert page.evaluate('document.querySelector("#detail-dialog").scrollWidth <= document.querySelector("#detail-dialog").clientWidth')
                    page.screenshot(path=str(output/f'detail-{width}.png'),full_page=False)
                    page.locator('#detail-dialog [data-close]').click()
            path=page.locator('#pie path').first
            path.focus()
            page.keyboard.press('Enter')
            assert page.locator('#drill').is_visible()
            assert not errors,errors
            browser.close()
        print('通过：虚构文件导入、财务数字、分类下钻、编辑、年度、1440/390/320px、弹窗和键盘操作。无 JavaScript 错误。')
    finally:
        server.close()
        thread.join(timeout=2)
