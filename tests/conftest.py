import io
import re
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
import ledger


@pytest.fixture
def setup(tmp_path):
    app=create_app(tmp_path,testing=True)
    (tmp_path/'password.hash').write_text(generate_password_hash('only-for-fictional-tests'))
    client=app.test_client()
    page=client.get('/login').text
    csrf=re.search(r'name="csrf" value="([^"]+)"',page)[1]
    assert client.post('/login',data={'csrf':csrf,'password':'only-for-fictional-tests'}).status_code==302
    with client.session_transaction() as session:
        token=session['csrf']
    headers={'X-CSRF-Token':token}
    assert client.post('/api/accounts',json={'name':'Fictional account A','kind':'credit','currency':'CAD'},headers=headers).status_code==200
    account=client.get('/api/data').json['accounts'][0]['id']
    return app,client,headers,account


def csv_bytes(rows):
    import csv
    buf=io.StringIO()
    writer=csv.DictWriter(buf,fieldnames=ledger.HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def row(**kwargs):
    return {'transaction_date':'2026-01-31','posting_date':'2026-02-02','description':'Fictional coffee','amount':'10.10',
            'currency':'CAD','type':'expense','status':'posted',**kwargs}


def upload(setup,rows,filename='fiction.csv',decisions=None,raw=None,coverage=None):
    _,client,headers,account=setup
    payload={'file':(io.BytesIO(raw or csv_bytes(rows)),filename),'account_id':account}
    if coverage:
        payload.update(coverage_start=coverage[0],coverage_end=coverage[1])
    preview=client.post('/api/import/preview',data=payload,headers=headers)
    assert preview.status_code==200,preview.json
    if preview.json.get('duplicate_file'):
        return preview.json
    commit=client.post('/api/import/commit',json={'token':preview.json['token'],'decisions':decisions or {}},headers=headers)
    assert commit.status_code==200,commit.json
    return commit.json
