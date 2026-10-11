export class RequestTimeoutError extends Error {
  constructor() {
    super('API request timed out')
    this.name = 'RequestTimeoutError'
  }
}

export async function withRequestTimeout(task, timeoutMs, parentSignal) {
  const controller = new AbortController()
  const abortFromParent = () => controller.abort(parentSignal?.reason)
  if (parentSignal?.aborted) abortFromParent()
  else parentSignal?.addEventListener('abort', abortFromParent, { once: true })

  let timeoutId
  const timeout = new Promise((_, reject) => {
    timeoutId = globalThis.setTimeout(() => {
      reject(new RequestTimeoutError())
      controller.abort()
    }, timeoutMs)
  })
  try {
    return await Promise.race([task(controller.signal), timeout])
  } finally {
    globalThis.clearTimeout(timeoutId)
    parentSignal?.removeEventListener('abort', abortFromParent)
  }
}
