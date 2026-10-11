import type { CasinoState } from '../types'
import {
  createPendingMutationStore,
  handlePendingMutationFailure,
  sendWithPendingMutation,
  type PendingMutation,
} from './pendingMutations.mjs'
import { isAllowedMutation, isPendingMutationRecord } from './mutationContract.mjs'
import { CasinoApiError, requestApi } from './httpClient'

const PENDING_REQUESTS_STORAGE_KEY = 'noir-casino.pending-requests.v1'
const SLOT_CLIENT_SEED_KEY = 'noir-casino.slot-client-seed.v1'
const FAIR_CLIENT_SEED_KEY = 'noir-casino.fair-client-seed.v1'
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

function fairClientSeed(): string {
  try {
    const existing = localStorage.getItem(FAIR_CLIENT_SEED_KEY)
    if (existing) return existing
    const seed = crypto.randomUUID()
    localStorage.setItem(FAIR_CLIENT_SEED_KEY, seed)
    return seed
  } catch {
    volatileSlotClientSeed ??= 'browser-' + requestKey()
    return volatileSlotClientSeed
  }
}

const pendingMutationStore = createPendingMutationStore(PENDING_REQUESTS_STORAGE_KEY)
const readPendingMutations = () => {
  const mutations = pendingMutationStore.read()
  if (!pendingMutationStore.isSafe()) {
    throw new CasinoApiError(
      'Сохранённая запись запроса повреждена; новые действия заблокированы.',
      0,
    )
  }
  if (Object.entries(mutations).some(([operation, pending]) => !isPendingMutationRecord(operation, pending))) {
    throw new CasinoApiError(
      'Сохранённая запись запроса не соответствует допустимому действию; новые действия заблокированы.',
      0,
    )
  }
  return mutations
}
const writePendingMutations = (value: Record<string, PendingMutation>) => pendingMutationStore.write(value)

export function hasPendingMutation(): boolean {
  try {
    if (!pendingMutationStore.isSafe()) return true
    return Object.keys(readPendingMutations()).length > 0
  } catch {
    return true
  }
}

export function isPendingMutationBlock(error: unknown): boolean {
  return error instanceof CasinoApiError && error.status === 0
}

export function isDefinitiveMutationRejection(error: unknown): boolean {
  return error instanceof CasinoApiError
    && error.status >= 400
    && error.status < 500
    && ![408, 409, 425, 429].includes(error.status)
}

export function reconciledConflictState(error: unknown): CasinoState | null {
  return error instanceof CasinoApiError && error.status === 409
    ? error.reconciledState ?? null
    : null
}

export async function requestMutation<T>(operation: string, path: string, payload: object): Promise<T> {
  if (!isAllowedMutation(operation, path, payload)) {
    throw new CasinoApiError('Недопустимый игровой запрос.', 0)
  }
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
  mutations[operation] = active
  const clearPending = (request: PendingMutation) => {
    const latest = readPendingMutations()
    if (latest[operation]?.key === request.key) {
      delete latest[operation]
      writePendingMutations(latest)
    }
  }
  return sendWithPendingMutation<T, PendingMutation>({
    active,
    persist: () => writePendingMutations(mutations),
    send: () => requestApi<T>(path, {
      method: 'POST',
      body: JSON.stringify({ ...payload, idempotency_key: active.key }),
    }),
    clear: clearPending,
    onFailure: (error: unknown) => handlePendingMutationFailure(error, {
      fetchState: () => requestApi<CasinoState>('/api/state'),
      clearPending: () => clearPending(active),
      isDefinitive: isDefinitiveMutationRejection,
      makeConflictError: (conflict, state) => {
        const apiConflict = conflict as CasinoApiError
        return new CasinoApiError(apiConflict.message, 409, state, apiConflict.code)
      },
      hasReconciledState: (failure) => failure instanceof CasinoApiError
        && Boolean(failure.reconciledState),
    }),
    persistenceError: () => new CasinoApiError(
      'Не удалось сохранить запрос для безопасного повтора. Действие не отправлено.',
      0,
    ),
  })
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

export function slotMutationPayload(
  bet: number,
  expectedServerSeedHash?: string,
): Record<string, unknown> {
  return {
    bet,
    choice: '',
    client_seed: slotClientSeed(),
    ...(expectedServerSeedHash ? { expected_server_seed_hash: expectedServerSeedHash } : {}),
  }
}

export function fairMutationPayload(
  bet: number,
  choice: string,
  expectedServerSeedHash?: string,
): Record<string, unknown> {
  return {
    bet,
    choice,
    client_seed: fairClientSeed(),
    ...(expectedServerSeedHash ? { expected_server_seed_hash: expectedServerSeedHash } : {}),
  }
}
