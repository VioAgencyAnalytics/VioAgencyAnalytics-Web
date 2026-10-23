
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes.pages import router as pages_router
from app.routes.reports import router as reports_router
from app.routes.video import router as video_router
from app.routes.demo_bundle import router as demo_bundle_router
from app.config import get_runtime_mode
from app.routes.published import router as published_router
from app.routes.viewer import router as viewer_router
from app.routes.handoff import router as handoff_router


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="VioAgencyAnalytics",
    description="Marketing analytics and reporting by VIO Agency",
    version="0.1.0",
)

# Static files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


# ==========================================
# HEALTH CHECK - Docker kiem tra endpoint nay
# ==========================================
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "kdh-report-dashboard",
    }


# ==========================================
# APPLICATION ROUTES
# ==========================================
app.include_router(viewer_router)
app.include_router(handoff_router)
app.include_router(published_router)
app.include_router(video_router)
app.include_router(pages_router)
app.include_router(reports_router)

# Report Bundle DEMO tu VioAgencyAnalytics-Admin
app.include_router(demo_bundle_router)


@app.middleware("http")
async def production_reports_only(request: Request, call_next):
    path = request.url.path

    # Production dashboards are reached through authenticated Bundle routes.
    # Legacy demonstration URLs stay available only outside production.
    public_paths = {
        "/",
        "/api/v1/health",
        "/login",
        "/logout",
        "/reports",
        "/auth/handoff/start",
        "/auth/handoff/callback",
    }

    public_prefixes = (
        "/static/",
        "/reports/",
        "/internal-preview/",
        "/published/",
    )

    if (
        get_runtime_mode().app_env == "production"
        and path not in public_paths
        and not path.startswith(public_prefixes)
    ):
        return JSONResponse(
            {"detail": "Not found"},
            status_code=404,
            headers={"Cache-Control": "no-store"},
        )

    return await call_next(request)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
