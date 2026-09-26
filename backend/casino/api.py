from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from casino.session import CasinoSession


class PlayRequest(BaseModel):
    bet: int = Field(gt=0)
    choice: str = ""
    idempotency_key: str = Field(min_length=1, max_length=128)


class BlackjackActionRequest(BaseModel):
    action: str = Field(pattern="^(hit|stand|double|split|surrender|insurance|decline_insurance)$")
    idempotency_key: str = Field(min_length=1, max_length=128)


class IdempotencyRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=128)


app = FastAPI(title="Noir Casino API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://tauri.localhost"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
casino = CasinoSession()


@app.exception_handler(RequestValidationError)
async def request_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    problems = "; ".join(
        f"{'.'.join(str(part) for part in item['loc'] if part != 'body')}: {item['msg']}"
        for item in error.errors()
    )
    return JSONResponse(status_code=422, content={"detail": f"Некорректный запрос: {problems}"})


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/state")
def get_state() -> dict:
    return casino.state()


@app.post("/api/games/{game_id}/play")
def play_game(game_id: str, request: PlayRequest) -> dict:
    try:
        return casino.play(game_id, request.bet, request.choice, request.idempotency_key)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/blackjack/start")
def start_blackjack(request: PlayRequest) -> dict:
    try:
        return casino.start_blackjack(request.bet, request.idempotency_key)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/blackjack/action")
def blackjack_action(request: BlackjackActionRequest) -> dict:
    try:
        return casino.blackjack_action(request.action, request.idempotency_key)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/refill")
def refill(request: IdempotencyRequest) -> dict:
    try:
        return {"balance": casino.refill(request.idempotency_key)}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
