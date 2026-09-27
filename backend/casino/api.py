from __future__ import annotations

import os
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from casino.errors import IdempotencyConflict, StaleGameState
from casino.session import CasinoSession

app = FastAPI(title="Noir Casino API", version="1.0.0")
app.state.api_token = os.environ.get("NOIR_CASINO_API_TOKEN")
app.state.api_instance_nonce = os.environ.get("NOIR_CASINO_API_INSTANCE_NONCE")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://tauri.localhost"],
    allow_origin_regex=r"^https?://(?:localhost|127\.0\.0\.1):\d+$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Noir-Api-Token"],
)
casino = CasinoSession()


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    expected_token = app.state.api_token
    if expected_token and request.method != "OPTIONS":
        provided_token = request.headers.get("X-Noir-Api-Token", "")
        if not secrets.compare_digest(
            provided_token.encode("utf-8"), expected_token.encode("utf-8")
        ):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def request_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    problems = "; ".join(
        f"{'.'.join(str(part) for part in item['loc'] if part != 'body')}: {item['msg']}"
        for item in error.errors()
    )
    return JSONResponse(status_code=422, content={"detail": f"Некорректный запрос: {problems}"})


@app.get("/api/health")
def health() -> dict:
    response = {"status": "ok"}
    if app.state.api_instance_nonce is not None:
        response["instance_nonce"] = app.state.api_instance_nonce
    return response


@app.get("/api/state", response_model=CasinoStateResponse, response_model_exclude_unset=True)
def get_state() -> dict:
    return casino.refresh_state()


@app.post(
    "/api/games/{game_id}/play", response_model=PlayResponseModel, response_model_exclude_unset=True
)
def play_game(game_id: str, request: PlayRequest) -> dict:
    try:
        return casino.play(
            game_id,
            request.bet,
            request.choice,
            request.idempotency_key,
            request.client_seed,
            request.expected_server_seed_hash,
        )
    except (IdempotencyConflict, StaleGameState) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post(
    "/api/blackjack/start", response_model=CasinoStateResponse, response_model_exclude_unset=True
)
def start_blackjack(request: PlayRequest) -> dict:
    try:
        return casino.start_blackjack(request.bet, request.idempotency_key)
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post(
    "/api/blackjack/action", response_model=CasinoStateResponse, response_model_exclude_unset=True
)
def blackjack_action(request: BlackjackActionRequest) -> dict:
    try:
        return casino.blackjack_action(request.action, request.idempotency_key)
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/refill", response_model=RefillResponse)
def refill(request: IdempotencyRequest) -> dict:
    try:
        return {"balance": casino.refill(request.idempotency_key)}
    except IdempotencyConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
