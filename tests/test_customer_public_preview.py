"""Public staging never replaces local origin/credentials or opens a service."""
import importlib.util
import json
from pathlib import Path
import pytest
from dotenv import dotenv_values
from test_customer_docker import setup


@pytest.mark.parametrize('origin', ['http://app.example.com','https://127.0.0.1','https://localhost',
    'https://a.localhost','https://user@app.example.com','https://app.example.com:8444',
    'https://app.example.com/path','https://app.example.com?code=private','https://app.example.com#private',
    'https://bad_host.example.com','https://app.example.com\n'])
def test_public_preview_rejects_ambiguous_or_insecure_origins_before_writing(setup,origin):
    module, folder, values = setup
    with pytest.raises(SystemExit): module.public_origin(origin)
    assert not list(folder.glob('*.env'))
    assert json.loads((folder/'config.json').read_text()) == values


def test_public_staging_preserves_local_files_and_credential_boundary(setup,monkeypatch):
    _,folder,values=setup
    root=Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('public_preview_test',root/'scripts/customer_public_preview.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (folder/'docker-web.env').write_text('QA_ONLY_LOCAL_ENV')
    result=module.stage('https://qa-preview.trycloudflare.com',folder)
    assert result['runtime_changed'] is False and result['callbacks_registered'] is False
    assert json.loads((folder/'config.json').read_text()) == values
    assert (folder/'docker-web.env').read_text() == 'QA_ONLY_LOCAL_ENV'
    web=dotenv_values(folder/'public-preview/docker-web.env',interpolate=False)
    admin=dotenv_values(folder/'public-preview/docker-admin.env',interpolate=False)
    assert web['CUSTOMER_WEB_ORIGIN']==admin['CUSTOMER_WEB_ORIGIN']==result['origin']
    assert not any('SECRET' in key or 'SMTP' in key or 'DATABASE' in key for key in web)
    assert admin['CUSTOMER_DATA_META_APP_SECRET']==values['CUSTOMER_DATA_META_APP_SECRET']
    assert set(result['callbacks'])=={'google_signin','google_data','meta'}
