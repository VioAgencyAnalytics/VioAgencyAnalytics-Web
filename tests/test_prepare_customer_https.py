"""Validate the trust boundary with temporary keys/config, never the OS store."""
from datetime import datetime, timezone, timedelta
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID
import pytest


@pytest.fixture
def helper(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / 'scripts'))
    spec = importlib.util.spec_from_file_location('prepare_customer_https_test', root / 'scripts/prepare_customer_https.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_certificate_is_not_a_ca_and_cannot_authenticate_other_hosts(helper, tmp_path):
    certificate = helper.prepare_certificate(tmp_path)
    cert = x509.load_pem_x509_certificate(certificate.read_bytes())
    keyfile = tmp_path / 'tls/private-key.pem'
    key = serialization.load_pem_private_key(keyfile.read_bytes(), password=None)
    cert.verify_directly_issued_by(cert)
    assert cert.public_key().public_numbers() == key.public_key().public_numbers()
    assert list(cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value) == [x509.DNSName('localhost')]
    assert not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    assert not usage.key_cert_sign and not usage.crl_sign
    assert list(cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value) == [ExtendedKeyUsageOID.SERVER_AUTH]
    assert cert.not_valid_after_utc <= datetime.now(timezone.utc) + timedelta(days=90)
    before = certificate.read_bytes(), keyfile.read_bytes()
    assert helper.prepare_certificate(tmp_path) == certificate
    assert (certificate.read_bytes(), keyfile.read_bytes()) == before


def test_incomplete_certificate_is_not_overwritten_or_trusted(helper, tmp_path):
    folder = tmp_path / 'tls'; folder.mkdir()
    key = folder / 'private-key.pem'; key.write_text('EXISTING_PRIVATE_FILE')
    with pytest.raises(SystemExit):
        helper.prepare_certificate(tmp_path)
    assert key.read_text() == 'EXISTING_PRIVATE_FILE'
    assert not (folder / 'certificate.pem').exists()


def test_activation_changes_only_origin_and_keeps_private_backup(helper, tmp_path):
    values = {'CUSTOMER_WEB_ORIGIN': 'http://127.0.0.1:8084',
              'CUSTOMER_SERVICE_TOKEN': 'SYNTHETIC_SERVICE_' + 'x' * 48,
              'DATABASE_URL': 'postgresql://vio_customer:qa@127.0.0.1:5434/vio_customer',
              'POSTGRES_PASSWORD': 'qa', 'ENCRYPTION_KEY': 'SYNTHETIC_KEY',
              'CUSTOMER_SMTP_PASSWORD': 'SYNTHETIC_SMTP', 'CUSTOMER_GOOGLE_CLIENT_SECRET': 'SYNTHETIC_GOOGLE',
              'CUSTOMER_DATA_META_APP_SECRET': 'SYNTHETIC_META'}
    original = json.dumps(values)
    (tmp_path / 'config.json').write_text(original)
    helper.activate_configuration(tmp_path)
    assert json.loads((tmp_path / 'config.json').read_text()) == {**values, 'CUSTOMER_WEB_ORIGIN': helper.ORIGIN}
    assert next((tmp_path / 'https-backup').glob('*/config.json')).read_text() == original
    assert not list(tmp_path.glob('https-stage-*'))


def test_activation_never_overwrites_a_public_configuration(helper, tmp_path):
    original = json.dumps({'CUSTOMER_WEB_ORIGIN': 'https://existing.example'})
    (tmp_path / 'config.json').write_text(original)
    with pytest.raises(SystemExit):
        helper.activate_configuration(tmp_path)
    assert (tmp_path / 'config.json').read_text() == original
    assert not (tmp_path / 'https-backup').exists()
