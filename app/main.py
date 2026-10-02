from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.database import create_db_and_tables
from app.routes.admin import router as admin_router
from app.routes.agenda import router as agenda_router
from app.routes.auth import router as auth_router
from app.routes.consultas import router as consultas_router
from app.routes.integracoes import router as integracoes_router
from app.security import limpar_rate_limits


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"

        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, private"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    limpar_rate_limits()
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    description="API REST de agendamento de consultas",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.obter_cors_origins(),
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
    expose_headers=[
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
    ],
)

app.add_middleware(SecurityHeadersMiddleware)


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(consultas_router)
app.include_router(agenda_router)
app.include_router(integracoes_router)


@app.get(
    "/health",
    tags=["Sistema"],
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}