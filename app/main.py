from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.api.errors import install_exception_handlers
from app.core.config import Settings, get_settings
from app.models import ApiEnvelope, HealthInfo
from app.services import build_services


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    services = build_services(runtime_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await services.repository.initialize()
        await services.manager.start()
        await services.sync.start()
        try:
            yield
        finally:
            await services.sync.stop()
            await services.manager.stop()

    application = FastAPI(
        title="Telegram Desk API",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.settings = runtime_settings
    application.state.services = services
    application.include_router(api_router)
    install_exception_handlers(application)

    assets_dir = runtime_settings.frontend_dist / "assets"
    application.mount(
        "/assets",
        StaticFiles(directory=assets_dir, check_dir=False),
        name="assets",
    )

    @application.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'"
        )
        return response

    @application.get("/api/health", response_model=ApiEnvelope[HealthInfo], tags=["system"])
    async def health() -> ApiEnvelope[HealthInfo]:
        return ApiEnvelope(data=HealthInfo())

    @application.get("/", include_in_schema=False)
    async def frontend():
        index_file = runtime_settings.frontend_dist / "index.html"
        if not index_file.is_file():
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "error": {
                        "code": "frontend_not_built",
                        "message": "Сначала выполните npm run build в каталоге frontend",
                    },
                },
            )
        return FileResponse(index_file, headers={"Cache-Control": "no-cache"})

    return application


app = create_app()
