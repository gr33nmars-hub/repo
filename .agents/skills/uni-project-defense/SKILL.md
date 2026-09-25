---
name: uni-project-defense
description: University term project structuring, documentation templates, presentation slide guidelines, and defense preparation for software engineering evaluations.
when_to_use: "Use when preparing university project documentation, academic defense slides, architectural justification, grading rubric alignment, or formulating answers to evaluator questions."
---

# University Project Architecture & Defense Guide

This skill helps package the casino application into a university-grade software engineering project worthy of an "A" (5 / Отлично).

---

## 1. Project Packaging & Academic Rubric Alignment

University evaluators typically grade on four pillars:
1. **Mathematical & Theoretical Foundation** (30%):
   - Formal specification of randomness, entropy sources, HMAC-SHA256 commitment scheme.
   - House Edge and RTP theorem with Monte Carlo convergence graphs ($N = 100,000$).
2. **System Architecture & Database Design** (30%):
   - Layered architecture (Presentation $\to$ Application/API $\to$ Domain Game Engines $\to$ Ledger Persistence).
   - 3NF / BCNF Database Schema with strict relational integrity, check constraints, and ACID isolation levels.
3. **Engineering Practices & Concurrency Safety** (20%):
   - Asynchronous I/O (WebSockets, FastAPI / asyncio).
   - Row-level locking (`SELECT ... FOR UPDATE`), idempotency UUIDs preventing double-spending.
   - Unit and integration tests with automated coverage report.
4. **UI/UX & Interactive Verification** (20%):
   - Polished responsive interface (built using Impeccable / Taste skills).
   - Dedicated "Fairness Verifier" tab allowing evaluators to verify past rounds independently in their browser without trusting the backend.

---

## 2. Standard Academic Documentation Outline

Include a comprehensive `DOCS/` or `README.md` with:
1. **Introduction & Motivation**: Problem statement of trust in online gaming, Provably Fair as a cryptographic solution.
2. **Architectural Overview**:
   - C4 Model (Context, Container, Component diagrams).
   - WebSocket state machine diagram for multiplayer / crash game loops.
3. **Cryptographic Algorithm Formalization**:
   - Explicit steps for seed generation, client seed rotation, HMAC truncation, and outcome mapping.
4. **Data Integrity & Concurrency**:
   - Transaction flow, sequence diagrams for bet placement and cashout.
5. **Experimental Results & Verification**:
   - Table of theoretical vs empirical RTP across 100,000 simulated games.
   - Concurrency stress test log (50 simultaneous threads).

---

## 3. Anticipated Professor Questions & Bulletproof Answers

| Typical Evaluator Question | Bulletproof Academic Answer |
| :--- | :--- |
| *"How do you prove the casino didn't change the outcome when the user placed a large bet?"* | *"We use a cryptographic commitment scheme. The hash $\text{SHA256}(S_{server})$ is delivered to the client before the bet is accepted. Since SHA-256 is second-preimage resistant, the server cannot find another seed producing the same hash. When the seed is revealed upon rotation, the player can verify the pre-image."* |
| *"What happens if a user clicks 'Bet' twice in 10 milliseconds?"* | *"Every client bet request includes a unique UUIDv4 `idempotency_key`. The ledger database uses a unique constraint on this key. Additionally, wallet balance updates use `SELECT ... FOR UPDATE` row locks, serializing access and guaranteeing no race condition or double deduction."* |
| *"Why not use Python's built-in `random` module?"* | *"`random` uses the Mersenne Twister (MT19937), which is not cryptographically secure and can be reverse-engineered after observing 624 outputs. We strictly use `secrets.token_hex` (OS CSPRNG from `/dev/urandom` / Windows CryptGenRandom) and HMAC-SHA256."* |
| *"How do you know the house actually maintains an edge?"* | *"Our automated test suite includes a Monte Carlo simulation (`tests/test_rtp.py`) executing 100,000 game cycles. The empirical RTP strictly converges to our theoretical target (97.3% for European Roulette, 97.0% for Crash) within a 95% confidence interval."* |
