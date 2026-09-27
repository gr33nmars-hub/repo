import assert from 'node:assert/strict'
import { webcrypto } from 'node:crypto'
import test from 'node:test'
import { verifySlotRound } from '../src/features/slots/slotFairness.mjs'

globalThis.crypto ??= webcrypto

const serverSeed = '00'.repeat(32)
const commitment = '60e05bd1b195af2f94112fa7197a5c88289058840ce7c6df9693756bc6250f55'
const strips = [
  ['🍋', '🍒', '🍋', '🔔', '💎', '🍋', '7️⃣', '🍋'],
  ['🍋', '🍋', '🍒', '🔔', '💎', '🍋', '7️⃣', '🍋'],
  ['🍋', '🍒', '🍋', '🔔', '💎', '🍋', '7️⃣', '🍋'],
]
const game = { reel_strips: strips, paytable: [{ symbol: '🍒', multiplier: 4 }], pair_multiplier: 1 }
const round = {
  bet: 10,
  payout: 40,
  symbols: ['🍒', '🍒', '🍒'],
  reel_stops: [1, 2, 1],
  fairness: {
    server_seed: serverSeed,
    server_seed_hash: commitment,
    client_seed: 'client-seed',
    nonce: 0,
  },
}

test('browser verifier accepts the Python HMAC stop and payout vector', async () => {
  assert.equal(await verifySlotRound(round, game, commitment), true)
})

test('browser verifier rejects a changed stop, symbol, payout, or commitment', async () => {
  assert.equal(await verifySlotRound({ ...round, reel_stops: [1, 3, 1] }, game, commitment), false)
  assert.equal(await verifySlotRound({ ...round, symbols: ['🍒', '🍋', '🍒'] }, game, commitment), false)
  assert.equal(await verifySlotRound({ ...round, payout: 39 }, game, commitment), false)
  assert.equal(await verifySlotRound(round, game, `${commitment.slice(0, -1)}0`), false)
})
