import assert from 'node:assert/strict'
import { webcrypto } from 'node:crypto'
import test from 'node:test'
import { verifyFairRound } from '../src/features/shared/fairness.mjs'

globalThis.crypto ??= webcrypto

const encoder = new TextEncoder()
const serverSeed = 'ab'.repeat(32)
const hex = (bytes) => Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
const canonical = (value) => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value)

async function digest(text) {
  return hex(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(text))))
}

async function fingerprint(version, rules) {
  return digest(canonical({ version, rules }))
}

async function hmac(message) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(serverSeed),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  return new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(message)))
}

async function bounded(clientSeed, stream, index, bound) {
  const range = 1n << 256n
  const limit = range - range % BigInt(bound)
  for (let counter = 0; ; counter += 1) {
    const value = BigInt(`0x${hex(await hmac(`${clientSeed}:0:${stream}:${counter}:${index}`))}`)
    if (value < limit) return Number(value % BigInt(bound))
  }
}

async function proof(clientSeed) {
  return {
    server_seed: serverSeed,
    server_seed_hash: await digest(serverSeed),
    client_seed: clientSeed,
    nonce: 0,
  }
}

test('roulette browser verifier accepts the deterministic pocket and rejects a changed pocket', async () => {
  const clientSeed = 'roulette-vector'
  const fairness = await proof(clientSeed)
  const rules = {
    wheel: Array.from({ length: 37 }, (_, number) => number),
    red_numbers: [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36],
    color_return_multiplier: 2,
    number_return_multiplier: 36,
  }
  const number = await bounded(clientSeed, 'roulette', 0, 37)
  const color = number === 0 ? 'zero' : rules.red_numbers.includes(number) ? 'red' : 'black'
  const round = {
    game_id: 'roulette',
    bet: 10,
    payout: 20,
    profit: 10,
    fairness,
    rule_version: 'roulette-v1',
    rules_fingerprint: await fingerprint('roulette-v1', rules),
    rules_snapshot: rules,
    outcome: { number, color, choice: color },
  }

  assert.equal(await verifyFairRound(round, undefined, fairness.server_seed_hash), true)
  assert.equal(await verifyFairRound({ ...round, outcome: { ...round.outcome, number: (number + 1) % 37 } }, undefined, fairness.server_seed_hash), false)
  assert.equal(await verifyFairRound({ ...round, outcome: { ...round.outcome, choice: 'invalid' }, payout: 0, profit: -10 }, undefined, fairness.server_seed_hash), false)
  assert.equal(await verifyFairRound({ ...round, payout: 19 }, undefined, fairness.server_seed_hash), false)
  assert.equal(await verifyFairRound({ ...round, profit: 0 }, undefined, fairness.server_seed_hash), false)
})

test('blackjack browser verifier accepts the shuffled draw prefix and rejects a changed draw', async () => {
  const score = (cards) => {
    let total = 0
    let aces = 0
    for (const card of cards) {
      const rank = card.slice(0, -1)
      if (rank === 'A') { total += 1; aces += 1 }
      else total += ['J', 'Q', 'K'].includes(rank) ? 10 : Number(rank)
    }
    return total + (aces > 0 && total + 10 <= 21 ? 10 : 0)
  }

  const rules = {
    decks: 1,
    natural_numerator: 3,
    natural_denominator: 2,
    late_surrender: true,
    insurance_profit_multiplier: 2,
    minimum_bet: 10,
    maximum_bet: 500,
    max_hands: 4,
    allow_double: true,
    allow_double_after_split: true,
    split_aces_one_card: true,
    split_aces_resplit: false,
    dealer_hits_soft_17: false,
  }

  let clientSeed = ''
  let draws = []
  for (let candidate = 0; candidate < 100; candidate += 1) {
    clientSeed = `blackjack-vector-${candidate}`
    const shoe = []
    for (const suit of ['♠', '♥', '♣', '♦']) {
      for (const rank of ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']) {
        shoe.push(`${rank}${suit}`)
      }
    }
    for (let index = shoe.length - 1; index > 0; index -= 1) {
      const other = await bounded(clientSeed, 'shuffle', index, index + 1)
      ;[shoe[index], shoe[other]] = [shoe[other], shoe[index]]
    }
    draws = shoe.slice(0, 4)
    if (score([draws[0], draws[2]]) !== 21
      && score([draws[1], draws[3]]) >= 17
      && score([draws[1], draws[3]]) !== 21) break
    clientSeed = ''
  }
  assert.notEqual(clientSeed, '', 'find a two-card surrender vector against a standing dealer')
  const fairness = await proof(clientSeed)
  const round = {
    game_id: 'blackjack',
    bet: 10,
    payout: 5,
    profit: -5,
    fairness,
    rule_version: 'blackjack-v1',
    rules_fingerprint: await fingerprint('blackjack-v1', rules),
    rules_snapshot: rules,
    outcome: {
      draw_order: draws,
      draw_events: [
        { card: draws[0], target: 'hand:0' },
        { card: draws[1], target: 'dealer' },
        { card: draws[2], target: 'hand:0' },
        { card: draws[3], target: 'dealer' },
      ],
      dealer_cards: [draws[1], draws[3]],
      hands: [{
        cards: [draws[0], draws[2]],
        bet: 10,
        status: 'surrendered',
        from_split: false,
        doubled: false,
        split_aces: false,
      }],
      initial_bet: 10,
      insurance_bet: 0,
      insurance_payout: 0,
    },
  }

  assert.equal(await verifyFairRound(round, undefined, fairness.server_seed_hash), true)
  assert.equal(await verifyFairRound({
    ...round,
    outcome: { ...round.outcome, draw_order: ['2♠', ...draws.slice(1)] },
  }, undefined, fairness.server_seed_hash), false)
  assert.equal(await verifyFairRound({
    ...round,
    outcome: {
      ...round.outcome,
      draw_events: [
        { card: draws[0], target: 'dealer' },
        { card: draws[1], target: 'hand:0' },
        { card: draws[2], target: 'dealer' },
        { card: draws[3], target: 'hand:0' },
      ],
    },
  }, undefined, fairness.server_seed_hash), false)
})
