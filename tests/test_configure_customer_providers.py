"""Application bootstrap keeps tenant grants and unrelated secrets untouched."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from dotenv import dotenv_values


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('configure_customer_providers_test',root/'scripts/configure_customer_providers.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    values={'CUSTOMER_WEB_ORIGIN':'http://127.0.0.1:8084','CUSTOMER_SERVICE_TOKEN':'QA_ONLY_SERVICE_'+'x'*48,
            'DATABASE_URL':'postgresql://vio_customer:qa-pass@127.0.0.1:5434/vio_customer',
            'POSTGRES_PASSWORD':'qa-pass','ENCRYPTION_KEY':'QA_ONLY_ENCRYPTION','CUSTOMER_SMTP_PASSWORD':'QA_ONLY_SMTP'}
    (tmp_path/'config.json').write_text(json.dumps(values))
    app={'APP_ID':'123456','APP_SECRET':'QA_ONLY_META_APP_SECRET','CONFIG_ID':'654321','GRAPH_VERSION':'v26.0'}
    monkeypatch.setattr(module,'primary_meta_application',lambda:app)
    return module,tmp_path,values,app


def test_content_only_reuses_app_settings_without_enabling_ads_or_touching_other_keys(fixture,capsys):
    module,folder,values,app=fixture
    module.configure('meta',folder,meta_source='content',reuse_primary=True)
    saved=json.loads((folder/'config.json').read_text())
    assert all(saved[k]==v for k,v in values.items())
    assert saved['CUSTOMER_DATA_META_CONTENT_CONFIG_ID']==app['CONFIG_ID']
    assert 'CUSTOMER_DATA_META_ADS_CONFIG_ID' not in saved
    web=dotenv_values(folder/'docker-web.env',interpolate=False)
    assert not any('META_' in key for key in web)
    out=capsys.readouterr().out
    assert app['APP_SECRET'] not in out and values['CUSTOMER_SMTP_PASSWORD'] not in out
    assert '/auth/customer/providers/meta/callback' in out


def test_existing_customer_app_is_not_silently_overwritten(fixture):
    module,folder,values,_=fixture
    values['CUSTOMER_DATA_META_APP_ID']='999999';before=json.dumps(values)
    (folder/'config.json').write_text(before)
    with pytest.raises(SystemExit):module.configure('meta',folder,meta_source='content',reuse_primary=True)
    assert (folder/'config.json').read_text()==before and not list(folder.glob('*.env'))


def test_invalid_database_preserves_config_and_all_existing_environment_files(fixture):
    module,folder,values,_=fixture
    values['DATABASE_URL']='postgresql://qa:qa@127.0.0.1:5434/primary';before=json.dumps(values)
    (folder/'config.json').write_text(before)
    (folder/'docker-admin.env').write_text('QA_ONLY_EXISTING_ENV')
    with pytest.raises(SystemExit):module.configure('meta',folder,meta_source='content',reuse_primary=True)
    assert (folder/'config.json').read_text()==before
    assert (folder/'docker-admin.env').read_text()=='QA_ONLY_EXISTING_ENV'
    assert not list(folder.glob('provider-prepare-*'))


def test_import_projects_only_app_keys_and_rejects_wrong_container_identity(fixture,monkeypatch):
    module,_,_,_=fixture
    # Read the original function, not the fixture's safe application stub.
    spec=importlib.util.spec_from_file_location('primary_reader_test',Path(module.__file__))
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    item={'Config':{'Labels':{'com.docker.compose.project':'vioagencyanaltics-admin','com.docker.compose.service':'admin'},
          'Env':['META_APP_ID=123456','META_APP_SECRET=QA_ONLY_APP_SECRET','META_CONFIG_ID=654321','META_GRAPH_VERSION=v26.0',
                 'CUSTOMER_SERVICE_TOKEN=QA_ONLY_SERVICE_SECRET','META_ACCESS_TOKEN=QA_ONLY_USER_TOKEN','DATABASE_URL=QA_ONLY_DATABASE']}}
    monkeypatch.setattr(reader.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=0,stdout=json.dumps([item])))
    app=reader.primary_meta_application()
    assert set(app)=={'APP_ID','APP_SECRET','CONFIG_ID','GRAPH_VERSION'}
    assert 'QA_ONLY_USER_TOKEN' not in json.dumps(app)
    item['Config']['Labels']['com.docker.compose.service']='web'
    with pytest.raises(SystemExit):reader.primary_meta_application()


def test_ads_configuration_uses_cloud_oauth_app_without_requesting_developer_token(fixture,monkeypatch,capsys):
    module,folder,values,_=fixture
    values.update(CUSTOMER_DATA_GOOGLE_CLIENT_ID='qa.apps.googleusercontent.com',
                  CUSTOMER_DATA_GOOGLE_CLIENT_SECRET='QA_ONLY_DATA_CLIENT_SECRET')
    (folder/'config.json').write_text(json.dumps(values))
    monkeypatch.setattr(module.getpass,'getpass',lambda *_:pytest.fail('No developer-token prompt allowed'))
    monkeypatch.setattr('builtins.input',lambda *_:pytest.fail('No application prompt needed'))
    module.configure('google-ads',folder)
    saved=json.loads((folder/'config.json').read_text())
    assert saved['CUSTOMER_DATA_GOOGLE_ADS_VERSION']=='v26'
    assert 'CUSTOMER_DATA_GOOGLE_ADS_DEVELOPER_TOKEN' not in saved
    out=capsys.readouterr().out
    assert 'Google sunset developer tokens on 2026-09-09' in out
    assert 'QA_ONLY_DATA_CLIENT_SECRET' not in out


def test_ads_setup_without_google_data_app_preserves_configuration(fixture):
    module,folder,_,_=fixture
    before=(folder/'config.json').read_text()
    with pytest.raises(SystemExit):module.configure('google-ads',folder)
    assert (folder/'config.json').read_text()==before
    assert not (folder/'docker-admin.env').exists()
