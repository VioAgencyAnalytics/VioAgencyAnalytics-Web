"""Source identity and local assets on the same protected, scoped report routes."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from app.customer_platform_brands import PLATFORM_BRANDS
from test_customer_auth import stack
from test_customer_data import prepare, report

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('source', sorted(PLATFORM_BRANDS))
def test_each_report_renders_its_own_brand_without_exposing_provider_fields(stack, source):
    client, _, state, _ = stack
    prepare(state)
    state['source_data'] = report(source)
    response = client.get('/workspace/reports/data', params={'source': source})
    assert response.status_code == 200
    assert f'data-platform-page="{source}"' in response.text
    assert '/static/customer/platforms/' + PLATFORM_BRANDS[source]['file'] in response.text
    assert 'NEVER_FORWARD' not in response.text
    assert 'premium.css?v=20261111' in response.text
    assert 'id="workspace-nav-toggle"' in response.text


def test_vendor_assets_are_pinned_local_files_with_no_executable_or_remote_svg_content():
    folder = ROOT / 'static/customer/platforms'
    manifest = json.loads((folder/'sources.json').read_text(encoding='utf-8'))
    records = {row['file']: row for row in manifest['assets']}
    for brand in PLATFORM_BRANDS.values():
        filename = brand['file']
        path = folder/filename
        assert path.parent == folder and path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == records[filename]['sha256']
        if path.suffix == '.svg':
            tree = ET.fromstring(path.read_bytes())
            for element in tree.iter():
                assert element.tag.split('}')[-1] not in {'script', 'foreignObject'}
                assert not any(key.lower().startswith('on') for key in element.attrib)
                for key, value in element.attrib.items():
                    if key.split('}')[-1] == 'href':
                        assert value.startswith(('#', 'data:image/'))
