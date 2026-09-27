function bytesToHex(bytes) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export async function verifySlotRound(round, game, announcedHash) {
  const proof = round.fairness
  const strips = game.reel_strips
  if (!proof || !strips || proof.nonce !== 0 || !/^[0-9a-f]{64}$/.test(proof.server_seed)
    || strips.length !== 3 || round.reel_stops?.length !== 3 || round.symbols?.length !== 3
    || proof.server_seed_hash !== announcedHash) return false

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
    let stop = null
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
    ? game.paytable?.find(({ symbol }) => symbol === symbols[0])?.multiplier
    : new Set(symbols).size === 2 ? game.pair_multiplier : 0
  return round.payout === round.bet * (multiplier ?? 0)
}
