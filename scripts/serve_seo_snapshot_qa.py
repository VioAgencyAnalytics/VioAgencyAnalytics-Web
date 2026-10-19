"""Isolated synthetic snapshot QA server: localhost only, no Admin or providers."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.mappers.bundle import BundleViewMapper
from app.mappers.dashboard import dashboard_context
from app.routes.pages import templates
from app.routes.published import HEADERS
from tests.test_seo_snapshot import seo_fixture

app = FastAPI()
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


@app.get('/reports/rpt_fixture_only')
def report(request: Request):
    raw = seo_fixture()
    bundle = BundleViewMapper().map(raw, raw['report']['id'], 2)
    context = dashboard_context(bundle, 'seo', request.url.path)
    return templates.TemplateResponse(request=request, name=context['snapshot_template'], context=context, headers=HEADERS)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=18084, access_log=False)
