import io
import json
import pytest
from openpyxl import Workbook
from conftest import upload


def preview(setup, raw, mapping=None, filename='fiction.csv', **fields):
    _, client, headers, account = setup
    payload={'account_id':account,'file':(io.BytesIO(raw),filename),**fields}
    if mapping is not None:
        payload['mapping']=json.dumps(mapping)
    return client.post('/api/import/preview',headers=headers,data=payload)


def commit(setup, response, decisions=None):
    return setup[1].post('/api/import/commit',headers=setup[2],json={'token':response.json['token'],'decisions':decisions or {}})


@pytest.mark.parametrize('separator',[',','\t',';'])
def test_user_header_aliases_and_delimiters(setup,separator):
    header=separator.join(['transaction_date','post_date','type','details','amount','currency'])
    values=separator.join(['2026-01-31','2026-02-02','expense','Entirely fictional coffee','10.10','CAD'])
    raw=(header+'\n'+values+'\n').encode()
    result=upload(setup,[],raw=raw)
    assert result['added']==1
    current=setup[1].get('/api/data').json['transactions'][0]
    assert (current['transaction_date'],current['posting_date'],current['description'],current['amount'])==('2026-01-31','2026-02-02','Entirely fictional coffee',1010)
    fid=current['sources'][0]['file_id']
    assert setup[1].get('/files/'+fid).data==raw


def test_missing_headers_return_mapping_and_no_private_rows(setup):
    raw=b'Date,Narrative,Value\n09/10/2026,Fictional unshared detail,10.10\n'
    result=preview(setup,raw)
    assert result.status_code==200
    assert result.json['mapping_required'] and result.json['headers']==['Date','Narrative','Value']
    assert 'Fictional unshared detail' not in result.text
    assert not setup[1].get('/api/data').json['transactions']


@pytest.mark.parametrize('format_name,expected',[('mdy','2026-09-10'),('dmy','2026-10-09')])
def test_explicit_date_mapping_persisted_commit(setup,format_name,expected):
    raw=b'Date,Narrative,Value\n09/10/2026,Fictional test,10.10\n'
    mapping={'columns':{'transaction_date':'Date','description':'Narrative','amount':'Value'},'date_format':format_name,'type_default':'expense'}
    p=preview(setup,raw,mapping)
    assert p.status_code==200,p.json
    assert p.json['rows'][0]['transaction_date']==expected
    assert commit(setup,p).json['added']==1
    row=setup[1].get('/api/data').json['transactions'][0]
    assert row['transaction_date']==expected and row['posting_date'] is None and row['currency']=='CAD'


def test_unknown_bank_type_cannot_silently_become_expense(setup):
    raw=b'Date,Narrative,Value,Kind\n2026-01-31,Fictional transaction,10.10,DEBIT\n'
    mapping={'columns':{'transaction_date':'Date','description':'Narrative','amount':'Value','type':'Kind'}}
    p=preview(setup,raw,mapping)
    assert p.json['rows'][0]['type']=='unconfirmed'
    assert p.json['rows'][0]['original_type']=='DEBIT'
    assert p.json['summary']['totals']['expense']==0
    assert p.json['summary']['totals']['income']==0
    assert p.json['summary']['totals']['unconfirmed']==1
    assert commit(setup,p).status_code==400
    assert not setup[1].get('/api/data').json['transactions']
    assert commit(setup,p,{'0':{'type':'payment'}}).status_code==200
    assert setup[1].get('/api/data').json['transactions'][0]['type']=='payment'


def test_explicit_positive_negative_rules(setup):
    raw=b'Date,Narrative,Value\n2026-01-31,Fictional purchase,-12.34\n2026-02-01,Fictional refund,5.00\n'
    base={'columns':{'transaction_date':'Date','description':'Narrative','amount':'Value'}}
    assert preview(setup,raw,base).status_code==400
    p=preview(setup,raw,{**base,'amount_mode':'signed','positive_type':'refund','negative_type':'expense'})
    assert p.json['summary']['totals']['expense']==1234
    assert p.json['summary']['totals']['refund']==500
    assert commit(setup,p).status_code==200
    assert {t['amount'] for t in setup[1].get('/api/data').json['transactions']}=={1234,500}


def test_xlsx_mapping_and_invalid_source_column(setup):
    wb=Workbook();ws=wb.active
    ws.append(['日期','说明','数额']);ws.append(['2026/01/31','完全虚构', '12.34'])
    buf=io.BytesIO();wb.save(buf)
    mapping={'columns':{'transaction_date':'日期','description':'说明','amount':'数额'},'date_format':'ymd_slash','type_default':'expense'}
    result=preview(setup,buf.getvalue(),mapping,filename='fiction.xlsx')
    assert commit(setup,result).status_code==200
    wrong={**mapping,'columns':{**mapping['columns'],'amount':'不存在的列'}}
    assert preview(setup,buf.getvalue(),wrong,filename='fiction-2.xlsx').json.get('duplicate_file')
    # Different bytes avoid the duplicate-file short circuit.
    ws.append(['2026/02/01','其他虚构','2.00']);buf=io.BytesIO();wb.save(buf)
    assert preview(setup,buf.getvalue(),wrong,filename='fiction-3.xlsx').status_code==400


def test_mapping_rejects_guessed_year_and_conflicting_alias_headers(setup):
    raw=b'Date,Narrative,Value\n01/02/26,Fictional test,1.00\n'
    mapping={'columns':{'transaction_date':'Date','description':'Narrative','amount':'Value'},'date_format':'mdy','type_default':'expense'}
    assert preview(setup,raw,mapping).status_code==400
    conflict=b'transaction_date,posting_date,post_date,description,amount,type\n2026-01-01,,,Fictional,1.00,expense\n'
    assert preview(setup,conflict).status_code==400


def test_mapped_and_canonical_overlapping_files_preserve_id(setup):
    raw=b'Date,Narrative,Value,ID\n01/31/2026,Fictional overlap,10.10,fictional-bank-id\n'
    mapping={'columns':{'transaction_date':'Date','description':'Narrative','amount':'Value','external_id':'ID'},'date_format':'mdy','type_default':'expense'}
    p=preview(setup,raw,mapping);assert commit(setup,p).json['added']==1
    original=setup[1].get('/api/data').json['transactions'][0]
    canonical=b'transaction_date,post_date,type,details,amount,currency,external_id\n2026-01-31,2026-02-02,expense,Fictional overlap,10.10,CAD,fictional-bank-id\n'
    assert upload(setup,[],raw=canonical)['duplicates']==1
    current=setup[1].get('/api/data').json['transactions'][0]
    assert current['id']==original['id'] and len(current['sources'])==2
