"""UI migration must retain local assets and the published report access boundary."""
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
from app.design_preview import app as preview
from app.routes.customer import CHANNELS, PAGES


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
        self.external_assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        url = attrs.get('href' if tag in ('a', 'link') else 'src', '')
        if tag == 'a' and url.startswith('/workspace'):
            self.links.add(url)
        if tag in ('link', 'script', 'img', 'iframe') and url.startswith(('http:', 'https:')):
            self.external_assets.append(url)


def test_all_nine_customer_screens_and_their_links_render_locally():
    with TestClient(preview) as client:
        links = set()
        for slug in PAGES:
            path = '/workspace' + ('/' + slug if slug else '')
            response = client.get(path)
            assert response.status_code == 200, path
            assert 'Bản xem thử' in response.text
            assert 'no-store' in response.headers['cache-control']
            parser = Links()
            parser.feed(response.text)
            assert not parser.external_assets, path
            links.update(parser.links)
        for path in links:
            assert client.get(path).status_code == 200, path


@pytest.mark.parametrize('slug,channel', CHANNELS.items())
def test_channel_hub_preserves_existing_reports_and_marks_missing_ones(slug, channel):
    with TestClient(preview) as client:
        response = client.get('/workspace/channels/' + slug)
        assert response.status_code == 200
        _, legacy_url = channel
        if legacy_url:
            assert f'src="{legacy_url}?workspace_embed=1"' in response.text
            report = client.get(legacy_url + '?workspace_embed=1')
            assert report.status_code == 200
            assert '/static/css/customer/report-embed.css' in report.text
        else:
            assert 'Chưa có dữ liệu' in response.text
            assert '<iframe' not in response.text


def test_customer_pages_cannot_bypass_production_or_create_server_state(monkeypatch):
    monkeypatch.setattr(main, 'get_runtime_mode', lambda: SimpleNamespace(app_env='production'))
    with TestClient(main.app) as client:
        for slug in PAGES:
            assert client.get('/workspace' + ('/' + slug if slug else '')).status_code == 404
        assert client.get('/workspace/channels/facebook-content').status_code == 404
    with TestClient(preview) as client:
        for path in ['/workspace/login', '/workspace/onboarding', '/workspace/members', '/workspace/settings']:
            response = client.post(path, json={'role': 'admin', 'email': 'test@example.invalid'})
            assert response.status_code == 405
            assert not response.cookies
        assert client.get('/workspace/unknown').status_code == 404
        assert client.get('/workspace/channels/unknown').status_code == 404
