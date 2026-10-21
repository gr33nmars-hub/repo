from __future__ import annotations

import os
import secrets
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from casino.api_errors import install_error_handlers
from casino.api_schemas import (
    BlackjackActionRequest,
    CasinoStateResponse,
    IdempotencyRequest,
    PlayRequest,
    RefillResponse,
)
from casino.api_schemas import (
    PlayResponse as PlayResponseModel,
)
from casino.application.service import CasinoService
from casino.persistence.sqlite import PlayerRepository


class _LazyCasinoService:
    """Delay the default SQLite composition until the first application request."""

    def __init__(self) -> None:
        self._service: CasinoService | None = None
        self._lock = Lock()

    def resolve(self) -> CasinoService:
        if self._service is not None:
            return self._service
        with self._lock:
            if self._service is None:
                self._service = CasinoService(PlayerRepository())
            return self._service

    def __getattr__(self, name: str):
        return getattr(self.resolve(), name)


casino: CasinoService | _LazyCasinoService = _LazyCasinoService()


def _default_casino_service() -> CasinoService:
    default = casino
    if isinstance(default, _LazyCasinoService):
        return default.resolve()
    return default


def create_app(casino_service: CasinoService | None = None) -> FastAPI:
    application = FastAPI(title="NOIR Casino Club API", version="1.0.0")
    install_error_handlers(application)
    application.state.api_token = os.environ.get("ASTORIA_CASINO_API_TOKEN")
    application.state.api_instance_nonce = os.environ.get("ASTORIA_CASINO_API_INSTANCE_NONCE")
    application.state.casino_service = casino_service
    application.state.request_shutdown = None
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://tauri.localhost",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Astoria-Api-Token"],
    )

    def service_for(request: Request) -> CasinoService:
        injected = request.app.state.casino_service
        return injected if injected is not None else _default_casino_service()

    @application.middleware("http")
    async def require_api_token(request: Request, call_next):
        expected_token = request.app.state.api_token
        if expected_token and request.url.path.startswith("/api/") and request.method != "OPTIONS":
            provided_token = request.headers.get("X-Astoria-Api-Token") or ""
            if not secrets.compare_digest(
                provided_token.encode("utf-8"), expected_token.encode("utf-8")
            ):
                return JSONResponse(
                    status_code=401,
                    content={"code": "unauthorized", "detail": "Unauthorized"},
                )
        return await call_next(request)

    @application.exception_handler(RequestValidationError)
    async def request_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'] if part != 'body')}: {item['msg']}"
            for item in error.errors()
        )
        return JSONResponse(
            status_code=422,
            content={
                "code": "invalid_request",
                "detail": f"Некорректный запрос: {problems}",
            },
        )

    @application.get("/api/health")
    def health(request: Request) -> dict:
        response = {"status": "ok"}
        if request.app.state.api_instance_nonce is not None:
            response["instance_nonce"] = request.app.state.api_instance_nonce
        return response

    @application.post("/api/shutdown", include_in_schema=False, response_model=None)
    def shutdown(request: Request) -> dict | JSONResponse:
        callback = request.app.state.request_shutdown
        if request.app.state.api_token is None or callback is None:
            return JSONResponse(
                status_code=404,
                content={"code": "not_found", "detail": "Not found"},
            )
        callback()
        return {"status": "shutting_down"}

    @application.get(
        "/api/state", response_model=CasinoStateResponse, response_model_exclude_unset=True
    )
    def get_state(request: Request) -> dict:
        return service_for(request).refresh_state()

    @application.post(
        "/api/games/{game_id}/play",
        response_model=PlayResponseModel,
        response_model_exclude_unset=True,
    )
    def play_game(game_id: str, body: PlayRequest, request: Request) -> dict:
        return service_for(request).play(
            game_id,
            body.bet,
            body.choice,
            body.idempotency_key,
            body.client_seed,
            body.expected_server_seed_hash,
        )

    @application.post(
        "/api/blackjack/start",
        response_model=CasinoStateResponse,
        response_model_exclude_unset=True,
    )
    def start_blackjack(body: PlayRequest, request: Request) -> dict:
        return service_for(request).start_blackjack(
            body.bet,
            body.idempotency_key,
            body.client_seed,
            body.expected_server_seed_hash,
            legacy_signature_compatible=not {
                "client_seed",
                "expected_server_seed_hash",
            }.intersection(body.model_fields_set),
        )

    @application.post(
        "/api/blackjack/action",
        response_model=CasinoStateResponse,
        response_model_exclude_unset=True,
    )
    def blackjack_action(body: BlackjackActionRequest, request: Request) -> dict:
        return service_for(request).blackjack_action(body.action, body.idempotency_key)

    @application.post("/api/refill", response_model=RefillResponse)
    def refill(body: IdempotencyRequest, request: Request) -> dict:
        return {"balance": service_for(request).refill(body.idempotency_key)}

    return application


app = create_app()
