export interface PendingMutation {
  key: string
  payload: string
}

export function createPendingMutationStore(
  storageKey: string,
  storageProvider: () => Storage = () => globalThis.localStorage,
): {
  read: () => Record<string, PendingMutation>
  write: (value: Record<string, PendingMutation>) => boolean
  isSafe: () => boolean
} {
  let memory: Record<string, PendingMutation> = {}
  let unsafe = false

  function read(): Record<string, PendingMutation> {
    let stored: string | null | undefined
    try {
      stored = storageProvider()?.getItem(storageKey)
    } catch {
      return memory
    }
    if (stored === null || stored === undefined) return memory

    let value: unknown
    try {
      value = JSON.parse(stored)
    } catch {
      unsafe = true
      return memory
    }
    if (
      value && typeof value === 'object' && !Array.isArray(value)
      && Object.values(value as Record<string, unknown>).every((request) => (
        request && typeof request === 'object'
        && typeof (request as Record<string, unknown>).key === 'string'
        && typeof (request as Record<string, unknown>).payload === 'string'
      ))
    ) {
      unsafe = false
      return value as Record<string, PendingMutation>
    }
    unsafe = true
    return memory
  }

  function isSafe(): boolean {
    return !unsafe
  }

  function write(value: Record<string, PendingMutation>): boolean {
    memory = value
    try {
      const storage = storageProvider()
      if (!storage) return false
      if (Object.keys(value).length) storage.setItem(storageKey, JSON.stringify(value))
      else storage.removeItem(storageKey)
      unsafe = false
      return true
    } catch {
      return false
    }
  }

  return { read, write, isSafe }
}

export async function sendWithPendingMutation<T, A = unknown>({
  active,
  persist,
  send,
  clear,
  onFailure,
  persistenceError,
}: {
  active: A
  persist: (active: A) => boolean
  send: (active: A) => Promise<T>
  clear: (active: A) => void | Promise<void>
  onFailure?: (error: unknown, active: A) => void | Promise<void>
  persistenceError: () => Error
}): Promise<T> {
  if (!persist(active)) throw persistenceError()
  try {
    const response = await send(active)
    await clear(active)
    return response
  } catch (error) {
    if (onFailure) await onFailure(error, active)
    throw error
  }
}

export async function handlePendingMutationFailure<E, S>(
  error: E,
  {
    fetchState,
    clearPending,
    isDefinitive,
    makeConflictError,
    hasReconciledState,
  }: {
    fetchState: () => Promise<S>
    clearPending: () => void | Promise<void>
    isDefinitive: (error: E) => boolean
    makeConflictError: (error: E, state: S) => Error
    hasReconciledState: (error: unknown) => boolean
  },
): Promise<never> {
  if ((error as { status?: number })?.status === 409) {
    try {
      const state = await fetchState()
      await clearPending()
      throw makeConflictError(error, state)
    } catch (reconciliationError) {
      if (hasReconciledState(reconciliationError)) throw reconciliationError
      throw error
    }
  }
  if (isDefinitive(error)) await clearPending()
  throw error
}
