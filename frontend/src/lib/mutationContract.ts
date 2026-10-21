const seededBetFields = ['bet', 'choice', 'client_seed', 'expected_server_seed_hash']
const actions = new Set(['hit', 'stand', 'double', 'split', 'surrender', 'insurance', 'decline_insurance'])

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function hasExactFields(value: unknown, fields: string[]): value is Record<string, unknown> {
  return isRecord(value)
    && Object.keys(value).every((key) => fields.includes(key))
    && fields.filter((key) => key !== 'expected_server_seed_hash').every((key) => Object.hasOwn(value, key))
}

function validSeededBet(payload: Record<string, unknown>, choices: string[]): boolean {
  return Number.isSafeInteger(payload.bet) && (payload.bet as number) > 0
    && typeof payload.choice === 'string' && choices.includes(payload.choice)
    && typeof payload.client_seed === 'string' && payload.client_seed.length <= 128
    && (payload.expected_server_seed_hash === undefined
      || typeof payload.expected_server_seed_hash === 'string'
        && /^[0-9a-f]{64}$/.test(payload.expected_server_seed_hash))
}

interface Contract {
  path: string
  validate: (payload: unknown) => boolean
}

const contracts: Record<string, Contract> = {
  'play:slots': {
    path: '/api/games/slots/play',
    validate: (payload) => hasExactFields(payload, seededBetFields) && validSeededBet(payload, ['']),
  },
  'play:roulette': {
    path: '/api/games/roulette/play',
    validate: (payload) => hasExactFields(payload, seededBetFields)
      && validSeededBet(payload, ['red', 'black', 'zero']),
  },
  'blackjack:start': {
    path: '/api/blackjack/start',
    validate: (payload) => hasExactFields(payload, seededBetFields) && validSeededBet(payload, ['']),
  },
  refill: {
    path: '/api/refill',
    validate: (payload) => isRecord(payload) && Object.keys(payload).length === 0,
  },
}

for (const action of actions) {
  contracts[`blackjack:${action}`] = {
    path: '/api/blackjack/action',
    validate: (payload) => isRecord(payload)
      && Object.keys(payload).length === 1
      && payload.action === action,
  }
}

export function isAllowedMutation(operation: string, path: string, payload: unknown): boolean {
  const contract = contracts[operation]
  return Boolean(contract && contract.path === path && contract.validate(payload))
}

export function isPendingMutationRecord(
  operation: string,
  request: unknown,
): request is { key: string; payload: string } {
  if (!request || typeof (request as Record<string, unknown>).key !== 'string') return false
  const r = request as { key: string; payload: unknown }
  if (r.key.length < 1 || r.key.length > 128 || typeof r.payload !== 'string') return false
  let saved: unknown
  try {
    saved = JSON.parse(r.payload)
  } catch {
    return false
  }
  return isRecord(saved) && Object.keys(saved).length === 2
    && typeof saved.path === 'string'
    && isAllowedMutation(operation, saved.path, saved.payload)
}
