from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from casino.api import create_app
from casino.api_schemas import CasinoStateResponse, PlayRequest
from casino.application.service import CasinoService
from casino.domain.models import GameResult
from casino.persistence.sqlite import PlayerRepository
from fastapi.testclient import TestClient

API_CONTRACT_FIXTURE = Path(__file__).parent / "fixtures" / "api-contract-v1.json"


@pytest.fixture
def api_context(tmp_path: Path):
    service = CasinoService(PlayerRepository(tmp_path / "casino.sqlite3"))
    application = create_app(service)
    application.state.api_token = None
    application.state.api_instance_nonce = None
    with TestClient(application) as client:
        yield application, client, service


def test_api_is_unguarded_when_no_token_is_configured(api_context) -> None:
    _, client, _ = api_context

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_configured_token_guards_health_and_state(api_context) -> None:
    application, client, _ = api_context
    application.state.api_token = "launch-secret"
    application.state.api_instance_nonce = "expected-nonce"
    contract = json.loads(API_CONTRACT_FIXTURE.read_text(encoding="utf-8"))

    missing = client.get("/api/health")
    wrong = client.get("/api/state", headers={"X-Astoria-Api-Token": "wrong"})
    valid = client.get("/api/health", headers={"X-Astoria-Api-Token": "launch-secret"})

    assert missing.status_code == contract["unauthorized"]["status"]
    assert sorted(missing.json()) == contract["unauthorized"]["fields"]
    assert wrong.status_code == contract["unauthorized"]["status"]
    assert wrong.json()["code"] == contract["unauthorized"]["code"]
    assert valid.status_code == 200
    assert valid.json()["instance_nonce"] == "expected-nonce"
    assert "launch-secret" not in valid.text


def test_shutdown_requires_token_and_only_runs_for_a_sidecar(api_context) -> None:
    application, client, _ = api_context
    calls: list[str] = []
    application.state.api_token = "shutdown-secret"
    application.state.request_shutdown = lambda: calls.append("requested")

    missing = client.post("/api/shutdown")
    valid = client.post("/api/shutdown", headers={"X-Astoria-Api-Token": "shutdown-secret"})

    assert missing.status_code == 401
    assert valid.status_code == 200
    assert valid.json() == {"status": "shutting_down"}
    assert calls == ["requested"]

    application.state.api_token = None
    application.state.request_shutdown = lambda: calls.append("unsafe")
    unavailable = client.post("/api/shutdown")
    assert unavailable.status_code == 404
    assert unavailable.json()["code"] == "not_found"
    assert calls == ["requested"]


def test_health_includes_only_the_current_instance_nonce(api_context) -> None:
    application, client, _ = api_context
    application.state.api_instance_nonce = "current-instance"
    assert client.get("/api/health").json()["instance_nonce"] == "current-instance"

    application.state.api_instance_nonce = "older-instance"
    assert client.get("/api/health").json()["instance_nonce"] == "older-instance"

    application.state.api_instance_nonce = None
    assert "instance_nonce" not in client.get("/api/health").json()


def test_cors_preflight_allows_auth_header_without_a_token(api_context) -> None:
    application, client, _ = api_context
    application.state.api_token = "launch-secret"

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-astoria-api-token",
        },
    )

    assert response.status_code == 200
    assert "x-astoria-api-token" in response.headers["access-control-allow-headers"].lower()


def test_cors_accepts_dev_origin_and_rejects_other_origins(api_context) -> None:
    _, client, _ = api_context
    preflight = {
        "Access-Control-Request-Method": "GET",
        "Origin": "http://127.0.0.1:5173",
    }

    allowed = client.options("/api/state", headers=preflight)
    wrong_port = client.options(
        "/api/state", headers={**preflight, "Origin": "http://127.0.0.1:5174"}
    )
    untrusted = client.options(
        "/api/state", headers={**preflight, "Origin": "https://attacker.example"}
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert wrong_port.status_code == 400
    assert "access-control-allow-origin" not in wrong_port.headers
    assert untrusted.status_code == 400
    assert "access-control-allow-origin" not in untrusted.headers


def test_request_schema_rejects_unknown_fields_and_state_matches_response_model(
    api_context,
) -> None:
    _, client, service = api_context
    with pytest.raises(ValueError):
        PlayRequest.model_validate(
            {"bet": 10, "choice": "red", "idempotency_key": "key", "extra": True}
        )

    state = service.state()
    validated = CasinoStateResponse.model_validate(client.get("/api/state").json())
    assert validated.player.balance == state["player"]["balance"]
    assert validated.blackjack is None


def test_http_response_models_preserve_the_public_contract(api_context) -> None:
    _, client, _ = api_context
    contract = json.loads(API_CONTRACT_FIXTURE.read_text(encoding="utf-8"))

    response = client.get("/api/state")
    assert response.status_code == contract["state"]["status"]
    state = response.json()
    assert sorted(state) == contract["state"]["top_level"]
    assert sorted(state["player"]) == contract["state"]["player"]
    assert (
        sorted(next(game for game in state["games"] if game["id"] == "slots"))
        == contract["state"]["slots_game"]
    )
    assert (
        sorted(next(game for game in state["games"] if game["id"] == "roulette"))
        == contract["state"]["roulette_game"]
    )
    assert state["blackjack"] is None
    assert "paytable" in next(game for game in state["games"] if game["id"] == "slots")
    assert "paytable" not in next(game for game in state["games"] if game["id"] == "roulette")

    played = client.post(
        "/api/games/roulette/play",
        json={"bet": 10, "choice": "red", "idempotency_key": "api-contract"},
    )
    assert played.status_code == contract["roulette_play"]["status"]
    result = played.json()
    assert sorted(result) == contract["roulette_play"]["top_level"]
    assert sorted(result["result"]) == contract["roulette_play"]["result"]
    assert "symbols" not in result["result"]
    assert result["result"]["rule_version"] == "roulette-v1"
    assert result["state"]["history"][0]["verification_status"] == "verified"

    extra_field = client.post(
        "/api/games/roulette/play",
        json={"bet": 10, "choice": "red", "idempotency_key": "extra-field", "ignored": 1},
    )
    assert extra_field.status_code == contract["validation_error"]["status"]
    assert sorted(extra_field.json()) == contract["validation_error"]["fields"]
    assert extra_field.json()["code"] == contract["validation_error"]["code"]

    invalid_choice = client.post(
        "/api/games/roulette/play",
        json={"bet": 10, "choice": "invalid", "idempotency_key": "bad-choice"},
    )
    assert invalid_choice.status_code == contract["domain_error"]["status"]
    assert sorted(invalid_choice.json()) == contract["domain_error"]["fields"]
    assert invalid_choice.json()["code"] == contract["domain_error"]["code"]


def test_ambiguous_legacy_idempotency_key_returns_conflict(api_context) -> None:
    _, client, service = api_context
    with closing(sqlite3.connect(service.repository.path)) as db:
        db.execute(
            "INSERT INTO processed_requests(request_key,response_json,signature) VALUES(?,?,NULL)",
            ("legacy-route-key", json.dumps({"balance": 7})),
        )
        db.commit()

    response = client.post("/api/refill", json={"idempotency_key": "legacy-route-key"})

    assert response.status_code == 409
    assert response.json()["code"] == "idempotency_conflict"
    assert "старой версии" in response.json()["detail"]


def test_lost_response_retries_same_key_once_after_service_restart(tmp_path: Path) -> None:
    path = tmp_path / "retry.sqlite3"
    first_service = CasinoService(PlayerRepository(path))
    application = create_app(first_service)
    request = {"bet": 10, "choice": "red", "idempotency_key": "lost-response-retry"}

    with TestClient(application) as client:
        first = client.post("/api/games/roulette/play", json=request)
        assert first.status_code == 200
        application.state.casino_service = CasinoService(PlayerRepository(path))

        retry = client.post("/api/games/roulette/play", json=request)
        conflict = client.post("/api/games/roulette/play", json={**request, "bet": 20})

    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert "другой операции" in conflict.json()["detail"]

    with closing(sqlite3.connect(path)) as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM processed_requests WHERE request_key=?",
                (request["idempotency_key"],),
            ).fetchone()[0]
            == 1
        )
        assert (
            db.execute(
                "SELECT COUNT(*) FROM ledger WHERE request_key=?", (request["idempotency_key"],)
            ).fetchone()[0]
            == 2
        )
        assert (
            db.execute("SELECT balance FROM profile WHERE id=1").fetchone()[0]
            == retry.json()["state"]["player"]["balance"]
        )


def test_legacy_blackjack_signature_matches_only_omitted_seed_fields(tmp_path: Path) -> None:
    path = tmp_path / "legacy-blackjack.sqlite3"
    service = CasinoService(PlayerRepository(path))
    key = "old-blackjack-api"
    old_signature = service._request_signature("blackjack.start", bet=20)
    cached_response = service.state()
    with closing(sqlite3.connect(path)) as db:
        db.execute(
            "INSERT INTO processed_requests(request_key,response_json,signature) VALUES(?,?,?)",
            (key, json.dumps(cached_response), old_signature),
        )
        db.commit()

    application = create_app(CasinoService(PlayerRepository(path)))
    with TestClient(application) as client:
        legacy = client.post("/api/blackjack/start", json={"bet": 20, "idempotency_key": key})
        explicit_seed = client.post(
            "/api/blackjack/start",
            json={"bet": 20, "client_seed": "", "idempotency_key": key},
        )

    assert legacy.status_code == 200
    assert legacy.json() == cached_response
    assert explicit_seed.status_code == 409
    assert explicit_seed.json()["code"] == "idempotency_conflict"


def test_stale_slot_commitment_returns_conflict_and_refreshes_state(tmp_path: Path) -> None:
    path = tmp_path / "shared.sqlite3"
    first_service = CasinoService(PlayerRepository(path))
    second_service = CasinoService(PlayerRepository(path))
    stale_hash = first_service.state()["slots_server_seed_hash"]
    second_service.play("slots", 10, "", "newer-spin", "client-seed")
    application = create_app(first_service)

    with TestClient(application) as client:
        response = client.post(
            "/api/games/slots/play",
            json={
                "bet": 10,
                "choice": "",
                "client_seed": "stale-client",
                "expected_server_seed_hash": stale_hash,
                "idempotency_key": "stale-spin",
            },
        )

    assert response.status_code == 409
    assert response.json()["code"] == "stale_game_state"
    assert "Seed" in response.json()["detail"]
    assert first_service.refresh_state()["player"]["rounds_played"] == 1


def test_failed_stale_refresh_keeps_the_in_memory_state_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "shared.sqlite3"
    stale_service = CasinoService(PlayerRepository(path))
    writer = CasinoService(PlayerRepository(path))

    def lose(bet: int, _: list[int]) -> GameResult:
        return GameResult("slots", "Слоты", "Проигрыш", bet, 0, "Тест")

    writer.games["slots"].play_at_stops = lose
    writer.play("slots", 2495, "", "drain-wallet")
    writer.refill("refill-wallet")
    old_state = stale_service.state()

    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE metadata SET value='invalid' WHERE key='server_seed'")

    with pytest.raises(RuntimeError, match="Server seed commitment"):
        stale_service.refresh_state()

    assert stale_service.state() == old_state
