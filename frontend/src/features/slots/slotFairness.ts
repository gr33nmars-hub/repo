import type { GameInfo, RoundResult } from '../../types'

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

export async function verifySlotRound(
  round: RoundResult,
  _game?: GameInfo,
  announcedHash?: string,
): Promise<boolean> {
  const proof = round.fairness
  const rules = round.rules_snapshot as {
    reels?: string[][]
    triples?: { symbol: string; multiplier: number }[]
    pair_multiplier?: number
  } | undefined

  const outcome = round.outcome as { reel_stops?: number[]; symbols?: string[] } | undefined

  if (!proof || proof.nonce !== 0 || !/^[0-9a-f]{64}$/.test(proof.server_seed)
    || round.rule_version !== 'slots-v1' || !round.rules_fingerprint || !rules
    || !Array.isArray(rules.reels) || !Array.isArray(rules.triples)
    || rules.triples.some((entry) => !entry || typeof entry.symbol !== 'string'
      || !Number.isSafeInteger(entry.multiplier) || entry.multiplier < 0)
    || !Number.isSafeInteger(rules.pair_multiplier) || (rules.pair_multiplier ?? 0) < 0
    || round.reel_stops?.length !== 3 || round.symbols?.length !== 3
    || !outcome || JSON.stringify(outcome.reel_stops) !== JSON.stringify(round.reel_stops)
    || JSON.stringify(outcome.symbols) !== JSON.stringify(round.symbols)
    || proof.server_seed_hash !== announcedHash) return false

  const strips = rules.reels
  if (strips.length !== 3) return false
  const fingerprintPayload = { version: round.rule_version, rules }
  const fingerprint = bytesToHex(new Uint8Array(await crypto.subtle.digest(
    'SHA-256', new TextEncoder().encode(canonicalJson(fingerprintPayload)),
  )))
  if (fingerprint !== round.rules_fingerprint) return false

  const encoder = new TextEncoder()
  const hash = await crypto.subtle.digest('SHA-256', encoder.encode(proof.server_seed))
  if (bytesToHex(new Uint8Array(hash)) !== announcedHash) return false
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(proof.server_seed), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  )
  for (let index = 0; index < 3; index += 1) {
    const strip = strips[index]
    if (!strip?.length) return false
    const length = BigInt(strip.length)
    const range = 1n << 256n
    const cutoff = range - range % length
    let stop: number | null = null
    for (let counter = 0; stop === null; counter += 1) {
      const digest = new Uint8Array(await crypto.subtle.sign(
        'HMAC', key, encoder.encode(`${proof.client_seed}:0:${index}:${counter}`),
      ))
      const candidate = BigInt(`0x${bytesToHex(digest)}`)
      if (candidate < cutoff) stop = Number(candidate % length)
    }
    if (round.reel_stops[index] !== stop || round.symbols[index] !== strip[stop]) return false
  }

  const symbols = round.symbols
  const multiplier = symbols[0] === symbols[1] && symbols[1] === symbols[2]
    ? rules.triples.find(({ symbol }) => symbol === symbols[0])?.multiplier
    : new Set(symbols).size === 2 ? rules.pair_multiplier : 0
  return round.payout === round.bet * (multiplier ?? 0)
}
