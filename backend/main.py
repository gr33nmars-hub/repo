"""
FastAPI REST API сервис игрового клуба NOIR Casino.
Предоставляет эндпоинты для настольных игр, криптографического модуля
Provably Fair (HMAC-SHA256) и управления игровым состоянием.
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import (
    get_player,
    deduct_balance,
    complete_round,
    refill_player,
    get_history,
    save_blackjack_state,
    load_blackjack_state,
    init_db,
    get_provably_fair_context,
    rotate_server_seed
)
from games.slots import get_slots_info, play_slots
from games.roulette import get_roulette_info, play_roulette
from games.blackjack import (
    get_blackjack_info,
    start_blackjack_round,
    perform_action,
    get_public_state
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация ресурсов при старте и освобождение при завершении."""
    init_db()
    yield

app = FastAPI(
    title="NOIR Casino Club API",
    description="Backend API with cryptographic Provably Fair outcomes (HMAC-SHA256) and ACID persistence.",
    version="2.0.0",
    lifespan=lifespan
)

# Строгая настройка CORS для локального десктопного запуска и веб-разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class PlayRequest(BaseModel):
    bet: int = Field(gt=0, description="Размер ставки в фишках")
    choice: Optional[str] = Field(default="red", description="Выбор исхода (для рулетки: red, black, zero)")

class BlackjackActionRequest(BaseModel):
    action: str = Field(description="Игровое действие: hit, stand, double, split, surrender, insurance, decline_insurance")

class RefillRequest(BaseModel):
    pass

def build_casino_state():
    """Сборка полного агрегированного состояния виртуального клуба."""
    player = get_player()
    raw_bj = load_blackjack_state()
    return {
        "player": player,
        "games": [get_slots_info(), get_roulette_info(), get_blackjack_info()],
        "history": get_history(15),
        "blackjack": get_public_state(raw_bj),
        "server_seed_hash": player.get("current_server_seed_hash")
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "NOIR Casino Club", "version": "2.0.0"}

@app.get("/api/state")
def get_state():
    return build_casino_state()

@app.post("/api/games/{game_id}/play")
def play_game(game_id: str, body: PlayRequest):
    player = get_player()
    bet = body.bet

    if bet <= 0:
        raise HTTPException(status_code=400, detail="Ставка должна быть положительной")
    if bet > player["balance"]:
        raise HTTPException(status_code=400, detail="Недостаточно фишек на балансе")

    # Получаем актуальный криптографический контекст (server_seed, client_seed, nonce)
    pf_ctx = get_provably_fair_context()

    if game_id == "slots":
        round_data = play_slots(
            bet=bet,
            server_seed=pf_ctx["server_seed"],
            client_seed=pf_ctx["client_seed"],
            nonce=pf_ctx["nonce"]
        )
    elif game_id == "roulette":
        round_data = play_roulette(
            bet=bet,
            choice=body.choice or "red",
            server_seed=pf_ctx["server_seed"],
            client_seed=pf_ctx["client_seed"],
            nonce=pf_ctx["nonce"]
        )
    else:
        raise HTTPException(status_code=404, detail="Запрашиваемый игровой зал не найден")

    saved_round = complete_round(
        game_id=round_data["game_id"],
        game_name=round_data["game_name"],
        message=round_data["message"],
        bet=round_data["bet"],
        payout=round_data["payout"],
        details=round_data["details"],
        symbols=round_data.get("symbols"),
        reel_stops=round_data.get("reel_stops"),
        outcome=round_data.get("outcome"),
        fairness=round_data.get("fairness"),
        already_deducted=False
    )

    return {
        "result": saved_round,
        "state": build_casino_state()
    }

@app.post("/api/blackjack/start")
def start_blackjack(body: PlayRequest):
    player = get_player()
    bet = body.bet

    if bet <= 0:
        raise HTTPException(status_code=400, detail="Ставка должна быть положительной")
    if bet > player["balance"]:
        raise HTTPException(status_code=400, detail="Недостаточно фишек на балансе")
    if bet % 2 != 0:
        raise HTTPException(status_code=400, detail="Для блэкджека ставка должна быть чётной")

    pf_ctx = get_provably_fair_context()
    state = start_blackjack_round(
        bet=bet,
        balance=player["balance"],
        server_seed=pf_ctx["server_seed"],
        client_seed=pf_ctx["client_seed"],
        nonce=pf_ctx["nonce"]
    )

    if state["status"] in ("won", "lost", "push"):
        total_payout = state.get("total_payout", 0)
        dealer_cards_str = " ".join(state["dealer_cards"])
        player_cards_str = " ".join(state["hands"][0]["cards"])
        details = f"{player_cards_str} против {dealer_cards_str}"
        complete_round(
            game_id="blackjack",
            game_name="Блэкджек",
            message=state["message"],
            bet=bet,
            payout=total_payout,
            details=details,
            fairness=state.get("fairness"),
            already_deducted=False
        )
        save_blackjack_state(state)
    else:
        deduct_balance(bet)
        save_blackjack_state(state)

    return build_casino_state()

@app.post("/api/blackjack/action")
def blackjack_action(body: BlackjackActionRequest):
    state = load_blackjack_state()
    if not state or state.get("status") not in ("playing", "insurance"):
        raise HTTPException(status_code=400, detail="Нет активной партии блэкджека")

    player = get_player()
    state, additional_bet = perform_action(state, body.action, player["balance"])

    if additional_bet > 0:
        if additional_bet > player["balance"]:
            raise HTTPException(status_code=400, detail="Недостаточно фишек для удвоения/сплита")
        deduct_balance(additional_bet)

    if state["status"] in ("won", "lost", "push", "mixed"):
        total_payout = state.get("total_payout", 0)
        total_bet = sum(h["bet"] for h in state["hands"]) + state.get("insurance_bet", 0)

        dealer_cards_str = " ".join(state["dealer_cards"])
        hands_str = " | ".join(" ".join(h["cards"]) for h in state["hands"])
        details = f"{hands_str} против {dealer_cards_str}"

        complete_round(
            game_id="blackjack",
            game_name="Блэкджек",
            message=state["message"],
            bet=total_bet,
            payout=total_payout,
            details=details,
            fairness=state.get("fairness"),
            already_deducted=True
        )
        save_blackjack_state(state)
    else:
        save_blackjack_state(state)

    return build_casino_state()

@app.post("/api/fairness/rotate")
def rotate_seed():
    """Ротация серверного сида для публичной верификации игроком."""
    result = rotate_server_seed()
    return {
        "status": "success",
        **result,
        "state": build_casino_state()
    }

@app.post("/api/refill")
def refill(body: RefillRequest):
    new_balance = refill_player()
    return {"balance": new_balance, "state": build_casino_state()}

if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    base_dir = os.path.dirname(backend_dir)

dist_path = os.path.join(base_dir, "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
