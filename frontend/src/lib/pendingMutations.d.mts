export interface PendingMutation {
  key: string
  payload: string
}

export function createPendingMutationStore(
  storageKey: string,
  storageProvider?: () => Storage,
): {
  read: () => Record<string, PendingMutation>
  write: (value: Record<string, PendingMutation>) => boolean
  isSafe: () => boolean
}

export function sendWithPendingMutation<T, A = unknown>(options: {
  active: A
  persist: (active: A) => boolean
  send: (active: A) => Promise<T>
  clear: (active: A) => void | Promise<void>
  onFailure?: (error: unknown, active: A) => void | Promise<void>
  persistenceError: () => Error
}): Promise<T>

export function handlePendingMutationFailure<E, S>(error: E, options: {
  fetchState: () => Promise<S>
  clearPending: () => void | Promise<void>
  isDefinitive: (error: E) => boolean
  makeConflictError: (error: E, state: S) => Error
  hasReconciledState: (error: unknown) => boolean
}): Promise<never>
