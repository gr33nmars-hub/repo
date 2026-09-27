import { isTauri } from '@tauri-apps/api/core'
import { Command, type Child } from '@tauri-apps/plugin-shell'
import type {
  BlackjackAction,
  CasinoState,
  GameId,
  PlayResponse,
  RouletteChoice,
} from '../types'
import { createPendingMutationStore, type PendingMutation } from './pendingMutations.mjs'

const apiBase = import.meta.env.VITE_CASINO_API ?? 'http://127.0.0.1:8765'
const API_TOKEN_ENV = 'NOIR_CASINO_API_TOKEN'
const API_TOKEN_HEADER = 'X-Noir-Api-Token'
const API_INSTANCE_NONCE_ENV = 'NOIR_CASINO_API_INSTANCE_NONCE'
const PENDING_REQUESTS_STORAGE_KEY = 'noir-casino.pending-requests.v1'
const SLOT_CLIENT_SEED_KEY = 'noir-casino.slot-client-seed.v1'
const requestKey = () => crypto.randomUUID()
let volatileSlotClientSeed: string | undefined

function slotClientSeed(): string {
  try {
    const existing = localStorage.getItem(SLOT_CLIENT_SEED_KEY)
    if (existing) return existing
    const seed = crypto.randomUUID()
    localStorage.setItem(SLOT_CLIENT_SEED_KEY, seed)
    return seed
  } catch {
    volatileSlotClientSeed ??= 'browser-' + requestKey()
    return volatileSlotClientSeed
  }
}
const pendingMutationStore = createPendingMutationStore(PENDING_REQUESTS_STORAGE_KEY)
const readPendingMutations = () => pendingMutationStore.read()
const writePendingMutations = (value: Record<string, PendingMutation>) => pendingMutationStore.write(value)
let backendChild: Child | undefined
let backendStartup: Promise<void> | undefined
let backendToken: string | undefined

class CasinoApiError extends Error {
  readonly status: number
  readonly reconciledState?: CasinoState

  constructor(message: string, status: number, reconciledState?: CasinoState) {
    super(message)
    this.name = 'CasinoApiError'
    this.status = status
    this.reconciledState = reconciledState
  }
}

export function isPendingMutationBlock(error: unknown): boolean {
  return error instanceof CasinoApiError && error.status === 0
}

export function reconciledConflictState(error: unknown): CasinoState | null {
  return error instanceof CasinoApiError && error.status === 409
    ? error.reconciledState ?? null
    : null
}

function createBackendToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32))
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

function apiHeaders(): Record<string, string> {
  return backendToken ? { [API_TOKEN_HEADER]: backendToken } : {}
}

async function waitForBackend(expectedNonce?: string): Promise<void> {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    let response: Response | undefined
    try {
      response = await fetch(`${apiBase}/api/health`, { headers: apiHeaders() })
    } catch {
      // Keep waiting while the bundled backend starts.
    }
    if (response?.ok) {
      try {
        const health = await response.json()
        if (health.status === 'ok' && (!expectedNonce || health.instance_nonce === expectedNonce)) return
      } catch {
        // A response without the expected health payload is not our backend.
      }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 250))
  }
  throw new Error('Не удалось запустить игру. Перезапусти приложение.')
}

export async function prepareBackend(): Promise<void> {
  if (!isTauri() || import.meta.env.DEV) {
    if (import.meta.env.DEV) {
      const startup = backendStartup ??= waitForBackend()
      try {
        await startup
      } catch (error) {
        if (backendStartup === startup) backendStartup = undefined
        throw error
      }
    }
    return
  }
  const startup = backendStartup ??= (async () => {
    const token = createBackendToken()
    const nonce = createBackendToken()
    backendToken = token

    const command = Command.sidecar('binaries/noir-api', [], {
      env: { [API_TOKEN_ENV]: token, [API_INSTANCE_NONCE_ENV]: nonce },
    })
    let child: Child | undefined
    const resetAfterExit = () => {
      if (!child || backendChild !== child) return
      backendChild = undefined
      backendStartup = undefined
      backendToken = undefined
    }
    command.on('close', resetAfterExit)
    command.on('error', resetAfterExit)
    child = await command.spawn()
    backendChild = child
    await waitForBackend(nonce)
  })()

  try {
    await startup
  } catch (error) {
    if (backendStartup === startup) {
      const child = backendChild
      backendChild = undefined
      backendStartup = undefined
      backendToken = undefined
      if (child) void child.kill().catch(() => undefined)
    }
    throw error
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  await prepareBackend()
  let response: Response
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...apiHeaders(), ...init?.headers },
    })
  } catch {
    throw new Error('Нет связи с игрой. Проверь соединение и повтори попытку.')
  }
  const body = await response.json()
  if (!response.ok) throw new CasinoApiError(body.detail ?? 'Запрос не прошёл', response.status)
  return body as T
}

async function requestMutation<T>(operation: string, path: string, payload: object): Promise<T> {
  const mutations = readPendingMutations()
  const serializedPayload = JSON.stringify({ path, payload })
  const pending = mutations[operation]
  if (Object.entries(mutations).some(([name]) => name !== operation)) {
    throw new CasinoApiError('Сначала повтори неподтверждённый запрос.', 0)
  }
  if (pending && pending.payload !== serializedPayload) {
    throw new CasinoApiError('Предыдущий запрос ещё не подтверждён. Повтори его с теми же параметрами.', 0)
  }
  const active: PendingMutation = pending ?? { key: requestKey(), payload: serializedPayload }
  if (!pending) {
    mutations[operation] = active
    writePendingMutations(mutations)
  }
  const response = await request<T>(path, {
    method: 'POST',
    body: JSON.stringify({ ...payload, idempotency_key: active.key }),
  }).catch(async (error: unknown) => {
    if (error instanceof CasinoApiError && error.status === 409) {
      try {
        const reconciledState = await request<CasinoState>('/api/state')
        const latest = readPendingMutations()
        if (latest[operation]?.key === active.key) {
          delete latest[operation]
          writePendingMutations(latest)
        }
        throw new CasinoApiError(error.message, 409, reconciledState)
      } catch (reconciliationError) {
        if (reconciliationError instanceof CasinoApiError && reconciliationError.reconciledState) {
          throw reconciliationError
        }
        throw error
      }
    }
    if (
      error instanceof CasinoApiError
      && error.status >= 400
      && error.status < 500
      && error.status !== 409
    ) {
      const latest = readPendingMutations()
      if (latest[operation]?.key === active.key) {
        delete latest[operation]
        writePendingMutations(latest)
      }
    }
    throw error
  })
  const latest = readPendingMutations()
  if (latest[operation]?.key === active.key) {
    delete latest[operation]
    writePendingMutations(latest)
  }
  return response
}

export async function retryPendingMutation(): Promise<boolean> {
  const [operation, pending] = Object.entries(readPendingMutations())[0] ?? []
  if (!operation || !pending) return false
  let saved: unknown
  try {
    saved = JSON.parse(pending.payload)
  } catch {
    throw new Error('Сохранённый запрос повреждён. Обнови состояние игры.')
  }
  if (
    !saved || typeof saved !== 'object'
    || typeof (saved as { path?: unknown }).path !== 'string'
    || !(saved as { payload?: unknown }).payload
    || typeof (saved as { payload: unknown }).payload !== 'object'
  ) {
    throw new Error('Сохранённый запрос повреждён. Обнови состояние игры.')
  }
  await requestMutation(operation, (saved as { path: string }).path, (saved as { payload: object }).payload)
  return true
}

export const casinoApi = {
  state: () => request<CasinoState>('/api/state'),
  play: (game: Exclude<GameId, 'blackjack'>, bet: number, choice = '', expectedServerSeedHash?: string) =>
    requestMutation<PlayResponse>(`play:${game}`, `/api/games/${game}/play`, {
      bet, choice, ...(game === 'slots' ? {
        client_seed: slotClientSeed(),
        ...(expectedServerSeedHash ? { expected_server_seed_hash: expectedServerSeedHash } : {}),
      } : {}),
    }),
  startBlackjack: (bet: number) =>
    requestMutation<CasinoState>('blackjack:start', '/api/blackjack/start', { bet }),
  blackjackAction: (action: BlackjackAction) =>
    requestMutation<CasinoState>(`blackjack:${action}`, '/api/blackjack/action', { action }),
  refill: () => requestMutation<{ balance: number }>('refill', '/api/refill', {}),
}

export function stopBackend(): void {
  const child = backendChild
  backendChild = undefined
  backendToken = undefined
  backendStartup = undefined
  if (child) void child.kill().catch(() => undefined)
}

export type { RouletteChoice }
