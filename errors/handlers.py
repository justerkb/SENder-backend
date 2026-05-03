"""Register global exception handlers on the FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from errors.exceptions import PackageGoException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PackageGoException)
    async def packagego_exception_handler(
        request: Request, exc: PackageGoException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
