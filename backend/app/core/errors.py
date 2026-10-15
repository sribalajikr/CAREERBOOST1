"""Standard JSON error envelope for every failed request."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "status": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = first.get("msg", "Invalid input")
        return JSONResponse(
            status_code=422,
            content={"detail": f"{loc}: {msg}" if loc else msg, "status": 422},
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our side. Please try again.", "status": 500},
        )
