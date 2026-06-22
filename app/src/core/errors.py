from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ApplicationError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: object | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class DependencyUnavailableError(ApplicationError):
    def __init__(self, dependency: str) -> None:
        super().__init__(
            status_code=503,
            code="DEPENDENCY_UNAVAILABLE",
            message="A required service is temporarily unavailable.",
            details={"dependency": dependency},
        )


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: object | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": get_request_id(request),
            },
        },
    )


async def application_error_handler(
    request: Request,
    error: ApplicationError,
) -> JSONResponse:
    return error_response(
        request=request,
        status_code=error.status_code,
        code=error.code,
        message=error.message,
        details=error.details,
    )


async def validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    fields: dict[str, list[str]] = {}
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"] if part != "body")
        fields.setdefault(location or "request", []).append(item["msg"])

    return error_response(
        request=request,
        status_code=400,
        code="VALIDATION_ERROR",
        message="The request data is invalid.",
        details={"fields": fields},
    )


async def http_error_handler(
    request: Request,
    error: HTTPException,
) -> JSONResponse:
    code = "NOT_FOUND" if error.status_code == 404 else "HTTP_ERROR"
    message = error.detail if isinstance(error.detail, str) else "Request failed."
    return error_response(
        request=request,
        status_code=error.status_code,
        code=code,
        message=message,
    )
