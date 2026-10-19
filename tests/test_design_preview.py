from fastapi.testclient import TestClient

from app.design_preview import app


def test_design_preview_opens_existing_overview_without_login():
    with TestClient(app) as client:
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == '/overview'
        response = client.get('/')
        assert response.status_code == 200
        assert 'Dữ liệu mẫu' in response.text
        assert 'dashboard-sidebar' in response.text
        assert 'type="password"' not in response.text


def test_design_preview_does_not_expose_real_report_or_auth_routes():
    with TestClient(app) as client:
        for path in ['/login', '/reports', '/auth/handoff/start', '/internal-preview/' + 'a' * 32,
                     '/reports/rpt_' + 'a' * 32 + '?revision=1', '/published/rpt_' + 'a' * 32]:
            assert client.get(path, follow_redirects=False).status_code == 404, path
        assert client.get('/api/v1/health').json()['data'] == 'demo'
