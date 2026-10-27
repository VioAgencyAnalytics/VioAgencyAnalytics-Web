from fastapi.testclient import TestClient

from app.design_preview import app


def test_design_preview_opens_new_customer_login_without_creating_identity():
    with TestClient(app) as client:
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == '/workspace/login'
        response = client.get('/')
        assert response.status_code == 200
        assert 'Bản xem thử' in response.text
        assert 'Khám phá giao diện mới' in response.text
        assert not response.cookies


def test_design_preview_does_not_expose_real_report_or_auth_routes():
    with TestClient(app) as client:
        for path in ['/login', '/reports', '/auth/handoff/start', '/internal-preview/' + 'a' * 32,
                     '/reports/rpt_' + 'a' * 32 + '?revision=1', '/published/rpt_' + 'a' * 32]:
            assert client.get(path, follow_redirects=False).status_code == 404, path
        assert client.get('/api/v1/health').json()['data'] == 'demo'
