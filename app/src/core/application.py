import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.core.config import Settings, settings
from src.core.database import engine
from src.core.errors import (
    ApplicationError,
    DependencyUnavailableError,
    application_error_handler,
    error_response,
    http_error_handler,
    validation_error_handler,
)
from src.router import api_router


logger = logging.getLogger(__name__)
request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = f"req_{uuid.uuid4().hex}"
        request.state.request_id = request_id
        token = bind_request_id(request_id)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - started_at) * 1000
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        finally:
            reset_request_id(token)


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s "
            "request_id=%(request_id)s %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def bind_request_id(request_id: str) -> Token[str]:
    return request_id_context.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    request_id_context.reset(token)


def check_database(database_engine: Engine) -> None:
    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise DependencyUnavailableError("database") from error


def create_operational_router(
    database_engine: Engine,
    application_settings: Settings,
) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def get_root() -> dict[str, str]:
        return {"message": "MenuScan API is running!"}

    @router.get("/health")
    def get_health() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready")
    def get_readiness() -> dict[str, str]:
        check_database(database_engine)
        email_ready = application_settings.email.is_configured()
        storage_ready = application_settings.storage.is_configured()
        return {
            "status": "ready" if email_ready and storage_ready else "degraded",
            "database": "ok",
            "email": "ok" if email_ready else "unconfigured",
            "storage": "ok" if storage_ready else "unconfigured",
        }

    return router


def create_app(
    *,
    application_settings: Settings | None = None,
    application_api_router: APIRouter | None = None,
    database_engine: Engine | None = None,
) -> FastAPI:
    current_settings = application_settings or settings
    current_api_router = application_api_router or api_router
    current_database_engine = database_engine or engine
    configure_logging(current_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application_started environment=%s",
            current_settings.app_env,
        )
        try:
            yield
        finally:
            current_database_engine.dispose()
            logger.info("application_stopped")

    application = FastAPI(
        title="MenuScan API",
        description="Restaurant menu digitization API",
        version="0.1.0",
        docs_url="/docs" if current_settings.app_env != "production" else None,
        redoc_url="/redoc" if current_settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(current_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextMiddleware)

    application.add_exception_handler(
        ApplicationError,
        application_error_handler,
    )
    application.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )
    application.add_exception_handler(HTTPException, http_error_handler)

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        logger.exception("unexpected_application_error", exc_info=error)
        return error_response(
            request=request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="An internal error occurred.",
        )

    application.include_router(
        create_operational_router(
            current_database_engine,
            current_settings,
        )
    )
    application.include_router(
        current_api_router,
        prefix=current_settings.api_v1_prefix,
    )
    return application
