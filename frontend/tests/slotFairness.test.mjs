import assert from 'node:assert/strict'
import { webcrypto } from 'node:crypto'
import test from 'node:test'
import { verifySlotRound } from '../src/features/slots/slotFairness.mjs'

globalThis.crypto ??= webcrypto

const serverSeed = '00'.repeat(32)
const commitment = '60e05bd1b195af2f94112fa7197a5c88289058840ce7c6df9693756bc6250f55'
const strips = [
  ['🍒', '🍋', '🔔', '🍒', '💎', '🍒', '🍋', '7️⃣'],
  ['🍋', '🍒', '💎', '🍋', '🍒', '🔔', '7️⃣', '🍒'],
  ['🍒', '🔔', '🍋', '🍒', '7️⃣', '🍋', '🍒', '💎'],
]
const rules = {
  reels: strips,
  triples: [
    { symbol: '7️⃣', multiplier: 24 },
    { symbol: '💎', multiplier: 12 },
    { symbol: '🔔', multiplier: 8 },
    { symbol: '🍒', multiplier: 4 },
    { symbol: '🍋', multiplier: 4 },
  ],
  pair_multiplier: 1,
}
const game = { reel_strips: strips, paytable: rules.triples, pair_multiplier: 1 }
const round = {
  bet: 10,
  payout: 10,
  symbols: ['🍒', '🍒', '🍋'],
  reel_stops: [5, 7, 5],
  outcome: { symbols: ['🍒', '🍒', '🍋'], reel_stops: [5, 7, 5] },
  rule_version: 'slots-v1',
  rules_fingerprint: 'aad98ee87483e677148b2801432076806d67e579dff2dcd8ba4aff6e500f2682',
  rules_snapshot: rules,
  fairness: {
    server_seed: serverSeed,
    server_seed_hash: commitment,
    client_seed: 'client-0',
    nonce: 0,
  },
}

test('browser verifier accepts the Python HMAC stop and payout vector', async () => {
  assert.equal(await verifySlotRound(round, game, commitment), true)
})

test('browser verifier rejects a changed stop, symbol, payout, or commitment', async () => {
  assert.equal(await verifySlotRound({ ...round, reel_stops: [5, 6, 5] }, game, commitment), false)
  assert.equal(await verifySlotRound({ ...round, symbols: ['🍒', '🍋', '🍒'] }, game, commitment), false)
  assert.equal(await verifySlotRound({ ...round, payout: 9 }, game, commitment), false)
  assert.equal(await verifySlotRound({ ...round, rules_fingerprint: '0'.repeat(64) }, game, commitment), false)
  assert.equal(await verifySlotRound(round, game, `${commitment.slice(0, -1)}0`), false)
})
