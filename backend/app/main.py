from contextlib import asynccontextmanager
import logging
import asyncio

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.body_limit import BodyLimit
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Avoid upstream request logging; credentials never enter application logs.
        logging.getLogger("httpx").setLevel(logging.WARNING)
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            app.state.http = client
            yield

    app = FastAPI(title="DEBUGGER API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.import_slots = asyncio.Semaphore(2)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=False,
    )

    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            {"error": {"message": str(exc.detail)}},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse({"error": {"message": "Invalid request."}}, status_code=422)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(router)
    return app
