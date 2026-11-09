"""Exercise the HTTP boundary without touching certificates or live accounts."""
from fastapi.testclient import TestClient
import pytest

from ops.customer_web_entrypoint import LOCAL_HTTPS_ORIGIN, local_https_redirect, tls_settings


def test_original_http_mode_does_not_require_tls_files():
    assert tls_settings({}) is None


@pytest.mark.parametrize('values', [
    {'CUSTOMER_LOCAL_TLS_CERT': 'missing'},
    {'CUSTOMER_LOCAL_TLS_KEY': 'missing'},
    {'CUSTOMER_LOCAL_TLS_CERT': 'missing', 'CUSTOMER_LOCAL_TLS_KEY': 'missing',
     'CUSTOMER_WEB_ORIGIN': LOCAL_HTTPS_ORIGIN},
])
def test_partial_tls_does_not_silently_serve_passwords_over_http(values):
    with pytest.raises(RuntimeError):
        tls_settings(values)


def test_only_the_explicit_local_tls_origin_can_enable_this_development_mode(tmp_path):
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    cert.write_text('synthetic certificate'); key.write_text('synthetic key')
    env = {'CUSTOMER_WEB_ORIGIN': LOCAL_HTTPS_ORIGIN,
           'CUSTOMER_LOCAL_TLS_CERT': str(cert), 'CUSTOMER_LOCAL_TLS_KEY': str(key)}
    assert tls_settings(env) == {'ssl_certfile': str(cert), 'ssl_keyfile': str(key)}
    for origin in ('http://127.0.0.1:8084', 'https://localhost:8444.evil.test', 'https://public.example'):
        with pytest.raises(RuntimeError):
            tls_settings({**env, 'CUSTOMER_WEB_ORIGIN': origin})


@pytest.fixture
def client():
    return TestClient(local_https_redirect, base_url='http://127.0.0.1:8084', follow_redirects=False)


def test_old_bookmarks_use_a_fixed_https_origin_without_forwarding_queries(client):
    response = client.get('/workspace/integrations?code=SYNTHETIC_CODE&state=SYNTHETIC_STATE',
                          headers={'Forwarded': 'host=evil.test;proto=http'})
    assert response.status_code == 307
    assert response.headers['location'] == LOCAL_HTTPS_ORIGIN + '/workspace/integrations'
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert 'set-cookie' not in response.headers


@pytest.mark.parametrize('path', ['/api/customer/auth/login', '/api/customer/session',
                                  '/auth/customer/google/callback?code=SYNTHETIC',
                                  '/auth/customer/providers/meta/callback?code=SYNTHETIC'])
def test_http_cannot_process_credentials_or_oauth_callbacks(client, path):
    for method in ('GET', 'POST'):
        response = client.request(method, path)
        assert response.status_code == 426
        assert 'location' not in response.headers and 'set-cookie' not in response.headers
        assert 'SYNTHETIC' not in response.text


@pytest.mark.parametrize('host', ['evil.test', 'localhost:8444', '127.0.0.1:8084.evil.test'])
def test_untrusted_host_cannot_create_an_open_redirect(client, host):
    response = client.get('/workspace', headers={'Host': host})
    assert response.status_code == 400
    assert 'location' not in response.headers


def test_post_is_not_replayed_to_https(client):
    response = client.post('/workspace/login', json={'password': 'SYNTHETIC_PASSWORD'})
    assert response.status_code == 426
    assert 'location' not in response.headers and 'SYNTHETIC_PASSWORD' not in response.text
