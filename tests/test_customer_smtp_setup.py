"""SMTP setup checks use fake transports and temporary configuration only."""
import importlib.util
import json
from pathlib import Path
import smtplib
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def smtp_setup(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'customer_dev.py'
    spec = importlib.util.spec_from_file_location('customer_dev_smtp_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CONFIG = tmp_path / 'config.json'
    values = {'CUSTOMER_GOOGLE_CLIENT_ID': 'existing-client', 'DATABASE_URL': 'existing-db'}
    module.CONFIG.write_text(json.dumps(values), encoding='utf-8')
    answers = iter(['', '', 'sender@example.test', 'sender@example.test'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    monkeypatch.setattr(module.getpass, 'getpass', lambda _: 'abcd efgh ijkl mnop')
    transport = MagicMock()
    monkeypatch.setattr(module.smtplib, 'SMTP', transport)
    return module, values, transport


def test_setup_checks_tls_auth_before_saving_preserves_other_settings(smtp_setup, capsys):
    module, values, transport = smtp_setup
    module.configure_smtp(values)
    saved = json.loads(module.CONFIG.read_text(encoding='utf-8'))
    assert all(saved[key] == value for key, value in values.items())
    assert saved['CUSTOMER_SMTP_PASSWORD'] == 'abcdefghijklmnop'
    assert saved['CUSTOMER_SMTP_TLS'] == 'true'
    transport.assert_called_once_with('smtp.gmail.com', 587, timeout=15)
    smtp = transport.return_value.__enter__.return_value
    assert [call[0] for call in smtp.method_calls] == ['starttls', 'login']
    assert 'abcdefghijklmnop' not in capsys.readouterr().out


@pytest.mark.parametrize('error', [smtplib.SMTPAuthenticationError(535, b'private server response'), OSError('private host')])
def test_failed_setup_keeps_existing_config_and_hides_server_response(smtp_setup, error):
    module, _, transport = smtp_setup
    before = module.CONFIG.read_bytes()
    transport.return_value.__enter__.return_value.login.side_effect = error
    with pytest.raises(SystemExit) as exc:
        module.configure_smtp(json.loads(before))
    assert 'private' not in str(exc.value)
    assert module.CONFIG.read_bytes() == before


def test_test_message_only_goes_to_explicit_recipient(smtp_setup, monkeypatch):
    module, values, transport = smtp_setup
    module.configure_smtp(values)
    transport.reset_mock()
    monkeypatch.setattr('builtins.input', lambda _: 'recipient@example.test')
    module.test_smtp(json.loads(module.CONFIG.read_text(encoding='utf-8')))
    message = transport.return_value.__enter__.return_value.send_message.call_args.args[0]
    assert message['To'] == 'recipient@example.test'
    assert message['From'] == 'sender@example.test'
    assert '#reset=' not in message.get_content()


@pytest.mark.parametrize('address', ['invalid', 'a@example.test\r\nBcc: x@example.test', 'a@example.test,b@example.test'])
def test_rejects_invalid_or_multiple_recipients(smtp_setup, address):
    module, _, _ = smtp_setup
    with pytest.raises(SystemExit):
        module.smtp_address(address)
