export function isAllowedMutation(operation: string, path: string, payload: unknown): boolean
export function isPendingMutationRecord(
  operation: string,
  request: unknown,
): request is { key: string; payload: string }
