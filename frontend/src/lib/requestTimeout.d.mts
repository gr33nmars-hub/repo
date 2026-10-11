export class RequestTimeoutError extends Error {}

export function withRequestTimeout<T>(
  task: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number,
  parentSignal?: AbortSignal | null,
): Promise<T>
