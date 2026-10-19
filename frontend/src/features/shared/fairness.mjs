import { verifySlotRound } from '../slots/slotFairness.mjs'

const encoder = new TextEncoder()
const hex = (bytes) => Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('')
const canonical = (value) => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object'
    ? `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`
    : JSON.stringify(value)

async function hmac(serverSeed, message) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(serverSeed),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  return new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(message)))
}

async function bounded(serverSeed, clientSeed, nonce, stream, index, bound) {
  const range = 1n << 256n
  const limit = range - range % BigInt(bound)
  for (let counter = 0; ; counter += 1) {
    const digest = await hmac(serverSeed, `${clientSeed}:${nonce}:${stream}:${counter}:${index}`)
    const value = BigInt(`0x${hex(digest)}`)
    if (value < limit) return Number(value % BigInt(bound))
  }
}

export async function verifyFairRound(round, game, commitment) {
  const proof = round?.fairness
  if (!proof || !/^[0-9a-f]{64}$/.test(proof.server_seed)
    || typeof proof.client_seed !== 'string' || !Number.isSafeInteger(proof.nonce)
    || proof.nonce < 0 || proof.server_seed_hash !== commitment) return false
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(proof.server_seed))
  if (hex(new Uint8Array(digest)) !== commitment) return false
  if (!round.rules_snapshot || !round.rule_version || !round.rules_fingerprint) return false
  const fingerprint = hex(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(
    canonical({ version: round.rule_version, rules: round.rules_snapshot }),
  ))))
  if (fingerprint !== round.rules_fingerprint) return false

  if (round.game_id === 'slots') return verifySlotRound(round, game, commitment)
  if (round.game_id === 'roulette') {
    const number = round.outcome?.number
    const rules = round.rules_snapshot
    const choice = round.outcome?.choice
    if (!Number.isSafeInteger(number) || number < 0 || number > 36
      || !['red', 'black', 'zero'].includes(choice)
      || !Array.isArray(rules.red_numbers)
      || !Number.isSafeInteger(rules.color_return_multiplier)
      || !Number.isSafeInteger(rules.number_return_multiplier)
      || !Number.isSafeInteger(round.bet) || round.bet < 0
      || !Number.isSafeInteger(round.payout) || round.payout < 0
      || !Number.isSafeInteger(round.profit)) return false
    const expected = await bounded(proof.server_seed, proof.client_seed, proof.nonce, 'roulette', 0, 37)
    if (number !== expected) return false
    const color = number === 0 ? 'zero' : rules.red_numbers.includes(number) ? 'red' : 'black'
    if (round.outcome.color !== color) return false
    const multiplier = choice === color
      ? color === 'zero' ? rules.number_return_multiplier : rules.color_return_multiplier
      : 0
    return round.payout === round.bet * multiplier && round.profit === round.payout - round.bet
  }
  if (round.game_id === 'blackjack') {
    const rules = round.rules_snapshot
    const shoe = []
    for (let deck = 0; deck < rules.decks; deck += 1) {
      for (const suit of ['♠', '♥', '♣', '♦']) {
        for (const rank of ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']) shoe.push(`${rank}${suit}`)
      }
    }
    for (let index = shoe.length - 1; index > 0; index -= 1) {
      const other = await bounded(proof.server_seed, proof.client_seed, proof.nonce, 'shuffle', index, index + 1)
      ;[shoe[index], shoe[other]] = [shoe[other], shoe[index]]
    }
    const draws = round.outcome?.draw_order
    const events = round.outcome?.draw_events
    const hands = round.outcome?.hands ?? []
    const dealer = []
    const allocated = hands.map(() => [])
    if (!(Array.isArray(draws) && draws.length > 0
      && draws.every((card, index) => card === shoe[index])
      && Array.isArray(events) && events.length === draws.length)) return false
    for (const [index, event] of events.entries()) {
      if (!event || typeof event !== 'object' || Array.isArray(event)
        || Object.keys(event).length !== 2 || event.card !== draws[index] || typeof event.target !== 'string') return false
      if (event.target === 'dealer') dealer.push(event.card)
      else if (/^hand:\d+$/.test(event.target)) {
        const handIndex = Number(event.target.slice(5))
        if (!Number.isSafeInteger(handIndex) || handIndex < 0 || handIndex >= allocated.length) return false
        allocated[handIndex].push(event.card)
      } else return false
    }
    if (canonical(dealer) !== canonical(round.outcome?.dealer_cards)
      || canonical(allocated) !== canonical(hands.map((hand) => hand.cards ?? []))) return false
    return true
  }
  return false
}
