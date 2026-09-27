CREATE TABLE profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    rounds_json TEXT NOT NULL,
    blackjack_json TEXT
);
INSERT INTO profile VALUES (1, 'Guest', 2490, '[]', NULL);
CREATE TABLE ledger (
    id INTEGER PRIMARY KEY,
    request_key TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    delta INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO ledger(request_key,entry_type,delta,balance_after)
VALUES ('legacy-loss', 'bet_stake', -10, 2490);
CREATE TABLE processed_requests (
    request_key TEXT PRIMARY KEY,
    response_json TEXT NOT NULL
);
INSERT INTO processed_requests VALUES ('old-key', '{"balance":2490}');
