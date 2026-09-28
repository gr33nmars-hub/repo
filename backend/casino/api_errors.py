"""Stable HTTP error responses for application and request failures."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from casino.application.errors import IdempotencyConflict, StaleGameState
from casino.domain.errors import InvalidCasinoCommand


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(IdempotencyConflict)
    async def idempotency_conflict(_: Request, error: IdempotencyConflict) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": "idempotency_conflict", "detail": str(error)},
        )

    @app.exception_handler(StaleGameState)
    async def stale_game_state(_: Request, error: StaleGameState) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"code": "stale_game_state", "detail": str(error)},
        )

    @app.exception_handler(InvalidCasinoCommand)
    async def invalid_request(_: Request, error: InvalidCasinoCommand) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"code": "invalid_request", "detail": str(error)},
        )
