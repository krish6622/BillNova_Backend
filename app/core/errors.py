"""Uniform error envelope and exception handlers (see docs §5.9)."""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error mapped to the standard error envelope."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_CREDENTIALS"


class TokenError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "TOKEN_INVALID"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN_ROLE"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class DuplicateError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "DUPLICATE_RESOURCE"


class PaymentMismatchError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "PAYMENT_MISMATCH"


class InsufficientStockError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "INSUFFICIENT_STOCK"


class SubscriptionLimitError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "SUBSCRIPTION_LIMIT_REACHED"


class SubscriptionInactiveError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "SUBSCRIPTION_INACTIVE"


def _envelope(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(
                "VALIDATION_ERROR", "Request validation failed.",
                {"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred."),
        )
