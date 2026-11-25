"""Notifications keep scoped action links and receipt updates."""
from app import customer_notifications as notifications
from test_customer_auth import csrf_headers, stack


WORKSPACE = 'a' * 32
CLIENT = 'b' * 32
SCOPE = {'workspace_id': WORKSPACE, 'client_id': CLIENT}
API = f'/api/customer/workspaces/{WORKSPACE}/notifications'


def test_list_validates_scope_and_projects_internal_links(stack, monkeypatch):
    client, _, _, _ = stack
    row = {'id': '1' * 64, 'kind': 'reconnect', 'at': None, 'title': 'GA4 cần kết nối lại',
           'detail': 'Cấp lại quyền đọc.', 'href': '/workspace/integrations?platform=ga4&reconnect=1',
           'action': 'Kết nối lại', 'source': 'ga4', 'attention': True, 'read': False}
    data = {'scope': SCOPE, 'items': [{**row, 'private_debug': 'DO_NOT_FORWARD'}]}

    async def backend(request, method, path):
        assert method == 'GET' and path.endswith('?client_id=' + CLIENT)
        return data

    monkeypatch.setattr(notifications, 'backend', backend)
    url = API + '?client_id=' + CLIENT
    result = client.get(url)
    assert result.status_code == 200 and result.json() == {'scope': SCOPE, 'items': [row]}
    assert client.get(url + '&client_id=' + CLIENT).status_code == 422
    data['items'][0]['href'] = '//foreign.example.test'
    assert client.get(url).status_code == 502
    data['items'] = []
    data['scope'] = {**SCOPE, 'client_id': '9' * 32}
    assert client.get(url).status_code == 502


def test_mark_read_requires_csrf_and_only_confirms_requested_ids(stack, monkeypatch):
    client, _, _, _ = stack
    async def backend(request, method, path, data):
        return {'read_ids': ['0' * 64]}

    monkeypatch.setattr(notifications, 'backend', backend)
    headers = csrf_headers(client)
    payload = {'client_id': CLIENT, 'ids': ['0' * 64]}
    assert client.post(API + '/read', json=payload).status_code == 403
    assert client.post(API + '/read', json=payload, headers=headers).json() == {'read_ids': payload['ids']}
    assert client.post(API + '/read', json={**payload, 'ids': ['1' * 64]}, headers=headers).status_code == 502
