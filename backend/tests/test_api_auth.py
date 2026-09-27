from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

_test_data = tempfile.TemporaryDirectory()
_previous_save_path = os.environ.get("NOIR_CASINO_SAVE_PATH")
os.environ["NOIR_CASINO_SAVE_PATH"] = str(Path(_test_data.name) / "casino.sqlite3")
from casino.api import app, casino  # noqa: E402 - configure isolated save path before import
from casino.api_schemas import CasinoStateResponse, PlayRequest  # noqa: E402
from casino.session import CasinoSession  # noqa: E402
from casino.storage import PlayerRepository  # noqa: E402

api_module = sys.modules["casino.api"]

if _previous_save_path is None:
    os.environ.pop("NOIR_CASINO_SAVE_PATH", None)
else:
    os.environ["NOIR_CASINO_SAVE_PATH"] = _previous_save_path


async def asgi_request(
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes]:
    response: dict[str, object] = {}
    response_body = bytearray()
    received_request = False
    request_headers = [
        (name.lower().encode("ascii"), value.encode("utf-8"))
        for name, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": request_headers,
        "client": ("testclient", 123),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, object]:
        nonlocal received_request
        if not received_request:
            received_request = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.Future()

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
            response["headers"] = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in message.get("headers", [])
            }
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    await app(scope, receive, send)
    return int(response["status"]), response["headers"], bytes(response_body)  # type: ignore[arg-type]


class ApiTokenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_token = app.state.api_token
        self.previous_nonce = app.state.api_instance_nonce

    def tearDown(self) -> None:
        app.state.api_token = self.previous_token
        app.state.api_instance_nonce = self.previous_nonce

    def test_api_remains_unguarded_when_no_token_is_configured(self) -> None:
        app.state.api_token = None
        app.state.api_instance_nonce = None

        status, _, body = asyncio.run(asgi_request("GET", "/api/health"))

        self.assertEqual(status, 200)
        self.assertNotIn("instance_nonce", json.loads(body))

    def test_configured_token_guards_health_and_state(self) -> None:
        app.state.api_token = "launch-secret"
        app.state.api_instance_nonce = "expected-nonce"

        missing_status, _, _ = asyncio.run(asgi_request("GET", "/api/health"))
        wrong_status, _, _ = asyncio.run(
            asgi_request("GET", "/api/state", {"X-Noir-Api-Token": "wrong"})
        )
        valid_status, _, valid_body = asyncio.run(
            asgi_request("GET", "/api/health", {"X-Noir-Api-Token": "launch-secret"})
        )

        self.assertEqual(missing_status, 401)
        self.assertEqual(wrong_status, 401)
        self.assertEqual(valid_status, 200)
        health = json.loads(valid_body)
        self.assertEqual(health["instance_nonce"], "expected-nonce")
        self.assertNotIn("launch-secret", valid_body.decode("utf-8"))

    def test_health_nonce_matches_only_the_configured_instance(self) -> None:
        app.state.api_token = None
        app.state.api_instance_nonce = "current-instance"
        matching_status, _, matching_body = asyncio.run(asgi_request("GET", "/api/health"))
        self.assertEqual(matching_status, 200)
        self.assertEqual(json.loads(matching_body).get("instance_nonce"), "current-instance")

        app.state.api_instance_nonce = "older-instance"
        _, _, mismatched_body = asyncio.run(asgi_request("GET", "/api/health"))
        self.assertNotEqual(json.loads(mismatched_body).get("instance_nonce"), "current-instance")

        app.state.api_instance_nonce = None
        _, _, missing_body = asyncio.run(asgi_request("GET", "/api/health"))
        self.assertNotIn("instance_nonce", json.loads(missing_body))

    def test_cors_preflight_allows_the_auth_header_without_a_token(self) -> None:
        app.state.api_token = "launch-secret"

        status, headers, _ = asyncio.run(
            asgi_request(
                "OPTIONS",
                "/api/health",
                {
                    "Origin": "http://tauri.localhost",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "x-noir-api-token",
                },
            )
        )

        self.assertEqual(status, 200)
        self.assertIn("x-noir-api-token", headers.get("access-control-allow-headers", "").lower())

    def test_cors_allows_loopback_dev_port_fallback_but_rejects_public_origin(self) -> None:
        allowed_status, allowed_headers, _ = asyncio.run(
            asgi_request(
                "OPTIONS",
                "/api/state",
                {
                    "Origin": "http://127.0.0.1:5174",
                    "Access-Control-Request-Method": "GET",
                },
            )
        )
        rejected_status, rejected_headers, _ = asyncio.run(
            asgi_request(
                "OPTIONS",
                "/api/state",
                {
                    "Origin": "https://attacker.example",
                    "Access-Control-Request-Method": "GET",
                },
            )
        )

        self.assertEqual(allowed_status, 200)
        self.assertEqual(
            allowed_headers.get("access-control-allow-origin"), "http://127.0.0.1:5174"
        )
        self.assertEqual(rejected_status, 400)
        self.assertNotIn("access-control-allow-origin", rejected_headers)

    def test_request_schema_rejects_unknown_fields_and_response_schema_matches_state(self) -> None:
        with self.assertRaises(ValueError):
            PlayRequest.model_validate(
                {"bet": 10, "choice": "red", "idempotency_key": "key", "extra": True}
            )

        with tempfile.TemporaryDirectory() as directory:
            state = CasinoSession(PlayerRepository(Path(directory) / "state.sqlite3")).state()
            validated = CasinoStateResponse.model_validate(state)
            self.assertEqual(validated.player.balance, state["player"]["balance"])
            self.assertIsNone(validated.blackjack)

    def test_http_response_models_preserve_public_payload_shape(self) -> None:
        status, _, body = asyncio.run(asgi_request("GET", "/api/state"))
        self.assertEqual(status, 200)
        state = json.loads(body)
        self.assertIsNone(state["blackjack"])
        self.assertIn("paytable", next(game for game in state["games"] if game["id"] == "slots"))
        self.assertNotIn(
            "paytable", next(game for game in state["games"] if game["id"] == "roulette")
        )

        status, _, body = asyncio.run(
            asgi_request(
                "POST",
                "/api/games/roulette/play",
                {"Content-Type": "application/json"},
                json.dumps(
                    {"bet": 10, "choice": "red", "idempotency_key": "api-contract"}
                ).encode(),
            )
        )
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertIn("result", result)
        self.assertNotIn("symbols", result["result"])
        self.assertIsNone(result["state"]["blackjack"])

        status, _, _ = asyncio.run(
            asgi_request(
                "POST",
                "/api/games/roulette/play",
                {"Content-Type": "application/json"},
                json.dumps(
                    {"bet": 10, "choice": "red", "idempotency_key": "extra-field", "ignored": 1}
                ).encode(),
            )
        )
        self.assertEqual(status, 422)

        status, _, _ = asyncio.run(
            asgi_request(
                "POST",
                "/api/games/roulette/play",
                {"Content-Type": "application/json"},
                json.dumps(
                    {"bet": 10, "choice": "invalid", "idempotency_key": "bad-choice"}
                ).encode(),
            )
        )
        self.assertEqual(status, 400)

    def test_ambiguous_legacy_idempotency_key_returns_conflict(self) -> None:
        db = sqlite3.connect(casino.repository.path)
        try:
            db.execute(
                "INSERT INTO processed_requests(request_key,response_json,signature) VALUES(?,?,NULL)",
                ("legacy-route-key", json.dumps({"balance": 7})),
            )
            db.commit()
        finally:
            db.close()

        status, _, body = asyncio.run(
            asgi_request(
                "POST",
                "/api/refill",
                {"Content-Type": "application/json"},
                json.dumps({"idempotency_key": "legacy-route-key"}).encode(),
            )
        )
        self.assertEqual(status, 409)
        self.assertIn("старой версии", json.loads(body)["detail"])

    def test_stale_slot_commitment_returns_conflict_and_refreshes_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shared.sqlite3"
            first = CasinoSession(PlayerRepository(path))
            second = CasinoSession(PlayerRepository(path))
            stale_hash = first.state()["slots_server_seed_hash"]
            second.play("slots", 10, "", "newer-spin", "client-seed")
            previous_api_session = api_module.casino
            api_module.casino = first
            try:
                status, _, body = asyncio.run(
                    asgi_request(
                        "POST",
                        "/api/games/slots/play",
                        {"Content-Type": "application/json"},
                        json.dumps(
                            {
                                "bet": 10,
                                "choice": "",
                                "client_seed": "stale-client",
                                "expected_server_seed_hash": stale_hash,
                                "idempotency_key": "stale-spin",
                            }
                        ).encode(),
                    )
                )
                self.assertEqual(status, 409)
                self.assertIn("Seed", json.loads(body)["detail"])
                self.assertEqual(first.refresh_state()["player"]["rounds_played"], 1)
            finally:
                api_module.casino = previous_api_session


if __name__ == "__main__":
    unittest.main()
