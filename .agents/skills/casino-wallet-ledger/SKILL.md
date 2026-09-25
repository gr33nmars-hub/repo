---
name: casino-wallet-ledger
description: Double-entry accounting, ACID database transactions, concurrency locking (SELECT FOR UPDATE), and idempotency protection for casino balances and bet settlements.
when_to_use: "Use when designing casino balances, transaction logs, bet processing, deposit/withdrawal APIs, race condition prevention, or demonstrating database concurrency integrity."
---

# Casino Wallet Ledger & Financial Concurrency

This skill enforces strict financial integrity, transactional safety, and double-entry bookkeeping for online casino backends.

---

## 1. Core Principles

1. **Never mutate balance directly with unvalidated arithmetic**:
   Always use database-level constraints (`CHECK (balance >= 0)`) and row-level locking (`SELECT ... FOR UPDATE`).
2. **Double-Entry Bookkeeping**:
   Every financial movement has an opposing entry.
   $$\sum \text{Debits} = \sum \text{Credits}$$
   Accounts involved:
   - `USER_WALLET` (User funds)
   - `CASINO_HOUSE_VAULT` (House balance / bankroll)
   - `BONUS_RESERVE` (Promotional credits)
3. **Idempotency Keys**:
   Every bet request must contain an `idempotency_key` (UUIDv4) supplied by the client to prevent double debits on network retry.

---

## 2. Relational Schema Pattern (PostgreSQL / SQLite)

```sql
-- 1. Wallets table with non-negative constraint
CREATE TABLE wallets (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users(id),
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    balance NUMERIC(18, 4) NOT NULL DEFAULT 0.0000 CHECK (balance >= 0),
    locked_balance NUMERIC(18, 4) NOT NULL DEFAULT 0.0000 CHECK (locked_balance >= 0),
    version INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Immutable Ledger Transactions
CREATE TYPE transaction_type AS ENUM ('DEPOSIT', 'WITHDRAWAL', 'BET_STAKE', 'BET_PAYOUT', 'BONUS');

CREATE TABLE ledger_transactions (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id),
    wallet_id UUID NOT NULL REFERENCES wallets(id),
    type transaction_type NOT NULL,
    amount NUMERIC(18, 4) NOT NULL, -- Negative for stake, positive for payout/deposit
    balance_after NUMERIC(18, 4) NOT NULL,
    game_round_id UUID,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ledger_user ON ledger_transactions(user_id, created_at DESC);
```

---

## 3. Atomic Bet Placement (SQLAlchemy / Python Pattern)

```python
from decimal import Decimal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

def place_bet_atomic(
    db: Session,
    user_id: UUID,
    amount: Decimal,
    idempotency_key: str,
    round_id: UUID
) -> dict:
    """
    Executes bet deduction under SELECT ... FOR UPDATE row lock.
    Guarantees no race conditions even under high concurrency.
    """
    assert amount > 0, "Bet amount must be positive"
    
    # 1. Check idempotency
    existing = db.execute(
        select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing:
        return {"status": "already_processed", "transaction_id": existing.id}

    # 2. Lock wallet row exclusively
    wallet = db.execute(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    ).scalar_one_or_none()

    if not wallet or wallet.balance < amount:
        raise InsufficientFundsError("Insufficient balance for bet")

    # 3. Apply balance deduction
    wallet.balance -= amount
    wallet.version += 1

    # 4. Record ledger entry
    ledger_entry = LedgerTransaction(
        idempotency_key=idempotency_key,
        user_id=user_id,
        wallet_id=wallet.id,
        type="BET_STAKE",
        amount=-amount,
        balance_after=wallet.balance,
        game_round_id=round_id
    )
    db.add(ledger_entry)
    db.commit()
    
    return {
        "status": "success",
        "new_balance": wallet.balance,
        "transaction_id": ledger_entry.id
    }
```

---

## 4. Academic Concurrency Benchmark (University Defense)

To demonstrate robustness to academic evaluators:
- Write a concurrency test (`pytest` with `asyncio.gather` or `ThreadPoolExecutor`) firing 50 simultaneous bet requests of \$10 on a wallet with \$100.
- Exactly 10 requests must succeed; exactly 40 must fail with `InsufficientFundsError`.
- Final balance must be exactly \$0.00 with zero negative slippage or anomalies.
