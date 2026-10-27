"""Nine-page customer workspace preview with the existing mock reports."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routes.pages import router as pages_router
from app.routes.reports import router as reports_router
from app.routes.video import router as video_router
from app.routes.customer import router as customer_router


app = FastAPI(title='VioAgencyAnalytics - Xem giao diện', docs_url=None, redoc_url=None, openapi_url=None)
app.state.customer_preview = True
app.mount('/static', StaticFiles(directory=str(Path(__file__).resolve().parents[1] / 'static')), name='static')


@app.get('/')
def index():
    return RedirectResponse('/workspace/login', status_code=303)


@app.get('/api/v1/health')
def health():
    return {'status': 'ok', 'mode': 'design_preview', 'data': 'demo'}


# No Admin repository, login, handoff, published Bundle or internal-preview router.
app.include_router(customer_router)
app.include_router(video_router)
app.include_router(pages_router)
app.include_router(reports_router)
