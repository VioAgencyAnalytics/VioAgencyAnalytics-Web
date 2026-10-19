"""Local UI QA only: synthetic fixtures, no database, Admin or providers."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.mappers.bundle import BundleViewMapper
from app.mappers.dashboard import dashboard_context
from app.routes.pages import templates
from app.routes.published import HEADERS
from qa_dashboard_fixture import paired_fixture
from tests.test_seo_snapshot import seo_fixture

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
originals, raw = paired_fixture()
raw['sections']['seo'] = seo_fixture()['sections']['seo']


@app.get('/')
@app.get('/overview')
def index():
    return RedirectResponse('/qa/overview', status_code=303)


@app.get('/api/v1/health')
def health():
    return {'status': 'ok', 'mode': 'design_preview', 'data': 'demo'}


@app.get('/qa/{channel}')
def report(request: Request, channel: str):
    selected = request.query_params.get('section', channel)
    if selected not in raw['sections']:
        raise HTTPException(404)
    bundle = BundleViewMapper().map(raw, raw['report']['id'], 2)
    context = dashboard_context(bundle, selected, request.url.path)
    return templates.TemplateResponse(request=request, name=context['snapshot_template'],
                                      context=context, headers=HEADERS)


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=18085, access_log=False)
