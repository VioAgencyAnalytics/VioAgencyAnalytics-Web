"""Docker credential separation uses temporary synthetic configuration only."""
import importlib.util
import json
from pathlib import Path

import pytest
from dotenv import dotenv_values


@pytest.fixture
def setup(tmp_path):
    path = Path(__file__).resolve().parents[1] / 'scripts/customer_docker.py'
    spec = importlib.util.spec_from_file_location('customer_docker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values = {
        'CUSTOMER_WEB_ORIGIN': 'http://127.0.0.1:8084',
        'CUSTOMER_SERVICE_TOKEN': 'test-only-service-' + 'x' * 48,
        'DATABASE_URL': 'postgresql://vio_customer:db-pass@127.0.0.1:5434/vio_customer',
        'POSTGRES_PASSWORD': 'db-pass', 'ENCRYPTION_KEY': 'fixture-key',
        'CUSTOMER_GOOGLE_CLIENT_SECRET': 'fixture-google-secret',
        'CUSTOMER_SMTP_PASSWORD': "smtp-$value#with'quote",
    }
    source = tmp_path / 'config.json'
    source.write_text(json.dumps(values), encoding='utf-8')
    return module, tmp_path, values


def test_secrets_are_separated_without_changing_existing_configuration(setup):
    module, folder, values = setup
    module.prepare(folder)
    web = dotenv_values(folder / 'docker-web.env', interpolate=False)
    admin = dotenv_values(folder / 'docker-admin.env', interpolate=False)
    postgres = dotenv_values(folder / 'docker-postgres.env', interpolate=False)
    assert set(web) == {'CUSTOMER_AUTH_ENABLED', 'CUSTOMER_WEB_ORIGIN',
                        'CUSTOMER_BACKEND_URL', 'CUSTOMER_SERVICE_TOKEN'}
    assert admin['CUSTOMER_SERVICE_TOKEN'] == web['CUSTOMER_SERVICE_TOKEN']
    assert admin['DATABASE_URL'] == 'postgresql://vio_customer:db-pass@customer-postgres:5432/vio_customer'
    assert admin['CUSTOMER_SMTP_PASSWORD'] == values['CUSTOMER_SMTP_PASSWORD']
    assert postgres['POSTGRES_PASSWORD'] == values['POSTGRES_PASSWORD']
    assert json.loads((folder / 'config.json').read_text()) == values


def test_wrong_database_scope_is_rejected_before_writing_env(setup):
    module, folder, values = setup
    values['DATABASE_URL'] = 'postgresql://vio_customer:db-pass@127.0.0.1:5434/legacy_reports'
    (folder / 'config.json').write_text(json.dumps(values), encoding='utf-8')
    with pytest.raises(SystemExit):
        module.prepare(folder)
    assert not list(folder.glob('*.env'))
