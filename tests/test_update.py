import io
from zipfile import ZipFile
import pytest
from scripts.update_code import update


def bundle(extra=None):
    buf=io.BytesIO()
    with ZipFile(buf,'w') as archive:
        for path in ['app.py','ledger.py','assets/app.js','templates/index.html']:
            archive.writestr('finance-main/'+path,'new fictional code')
        if extra:
            archive.writestr('finance-main/'+extra,'must not replace private data')
    return buf.getvalue()


def test_update_preserves_private_database_password_and_venv(tmp_path):
    (tmp_path/'app.py').write_text('old code')
    (tmp_path/'ledger.py').write_text('old ledger')
    private=tmp_path/'.runtime';private.mkdir()
    (private/'ledger.sqlite3').write_bytes(b'fictional database sentinel')
    (private/'password.hash').write_text('fictional password sentinel')
    (private/'files').mkdir();(private/'files'/'fixture').write_bytes(b'fictional bill sentinel')
    (tmp_path/'.venv').mkdir();(tmp_path/'.venv'/'sentinel').write_text('keep dependencies')
    count,backup=update(tmp_path,bundle())
    assert count==4 and (tmp_path/'app.py').read_text()=='new fictional code'
    assert (private/'ledger.sqlite3').read_bytes()==b'fictional database sentinel'
    assert (private/'password.hash').read_text()=='fictional password sentinel'
    assert (private/'files'/'fixture').read_bytes()==b'fictional bill sentinel'
    assert (tmp_path/'.venv'/'sentinel').read_text()=='keep dependencies'
    with ZipFile(backup) as archive:
        assert archive.read('app.py')==b'old code'
        assert not any('.runtime' in name for name in archive.namelist())


@pytest.mark.parametrize('extra',['.runtime/password.hash','../outside.py','private/statement.csv'])
def test_update_rejects_private_or_escaping_paths_without_changes(tmp_path,extra):
    (tmp_path/'app.py').write_text('old code');(tmp_path/'ledger.py').write_text('old ledger')
    with pytest.raises(ValueError):
        update(tmp_path,bundle(extra))
    assert (tmp_path/'app.py').read_text()=='old code'
