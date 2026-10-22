import { withRequestTimeout } from '../lib/requestTimeout.ts'

export async function waitForBackend(
  url: string,
  headers: Record<string, string>,
  startupTimeoutMs = 15_000,
): Promise<void> {
  const deadline = Date.now() + startupTimeoutMs
  while (Date.now() < deadline) {
    try {
      const ready = await withRequestTimeout(async (signal) => {
        const response = await fetch(url, { headers, signal })
        return response.ok && (await response.json()).status === 'ok'
      }, Math.min(1000, deadline - Date.now()))
      if (ready) return
    } catch {
      // Health probes may fail while the local process is starting.
    }
    const remaining = deadline - Date.now()
    if (remaining > 0) await new Promise((resolve) => setTimeout(resolve, Math.min(250, remaining)))
  }
  throw new Error('Локальный сервер не запустился. Перезапусти приложение.')
}
