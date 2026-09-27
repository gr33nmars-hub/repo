export interface PendingMutation {
  key: string
  payload: string
}

export function createPendingMutationStore(
  storageKey: string,
  storageProvider?: () => Storage,
): {
  read: () => Record<string, PendingMutation>
  write: (value: Record<string, PendingMutation>) => void
}
