export class RequestTimeoutError extends Error {
  constructor() {
    super('API request timed out')
    this.name = 'RequestTimeoutError'
  }
}

export async function withRequestTimeout<T>(
  task: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number,
  parentSignal?: AbortSignal | null,
): Promise<T> {
  const controller = new AbortController()
  const abortFromParent = () => controller.abort(parentSignal?.reason)
  if (parentSignal?.aborted) {
    abortFromParent()
  } else {
    parentSignal?.addEventListener('abort', abortFromParent, { once: true })
  }

  let timeoutId: ReturnType<typeof globalThis.setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = globalThis.setTimeout(() => {
      reject(new RequestTimeoutError())
      controller.abort()
    }, timeoutMs)
  })
  try {
    return await Promise.race([task(controller.signal), timeout])
  } finally {
    if (timeoutId !== undefined) {
      globalThis.clearTimeout(timeoutId)
    }
    parentSignal?.removeEventListener('abort', abortFromParent)
  }
}
