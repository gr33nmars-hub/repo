import { isTauri } from '@tauri-apps/api/core'
import { Command, type Child } from '@tauri-apps/plugin-shell'
import type {
  BlackjackAction,
  CasinoState,
  GameId,
  PlayResponse,
  RouletteChoice,
} from '../types'

const apiBase = import.meta.env.VITE_CASINO_API ?? 'http://127.0.0.1:8765'
const requestKey = () => crypto.randomUUID()
const pendingRequestKeys = new Map<string, string>()
let backendChild: Child | undefined
let backendStartup: Promise<void> | undefined

async function waitForBackend(): Promise<void> {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`${apiBase}/api/health`)
      if (response.ok) return
    } catch {
      await new Promise((resolve) => window.setTimeout(resolve, 250))
    }
  }
  throw new Error('Игровой сервер не запустился. Перезапусти приложение.')
}

export async function prepareBackend(): Promise<void> {
  if (!isTauri() || import.meta.env.DEV) {
    if (import.meta.env.DEV) {
      backendStartup ??= waitForBackend()
      await backendStartup
    }
    return
  }
  backendStartup ??= (async () => {
    backendChild = await Command.sidecar('binaries/noir-api').spawn()
    await waitForBackend()
  })()
  await backendStartup
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  await prepareBackend()
  let response: Response
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new Error('Нет связи с игровым сервером. Проверь, что API запущен.')
  }
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail ?? 'Запрос не прошёл')
  return body as T
}

async function requestMutation<T>(operation: string, path: string, payload: object): Promise<T> {
  const key = pendingRequestKeys.get(operation) ?? requestKey()
  pendingRequestKeys.set(operation, key)
  const response = await request<T>(path, {
    method: 'POST',
    body: JSON.stringify({ ...payload, idempotency_key: key }),
  })
  pendingRequestKeys.delete(operation)
  return response
}

export const casinoApi = {
  state: () => request<CasinoState>('/api/state'),
  play: (game: Exclude<GameId, 'blackjack'>, bet: number, choice = '') =>
    requestMutation<PlayResponse>(`play:${game}`, `/api/games/${game}/play`, { bet, choice }),
  startBlackjack: (bet: number) =>
    requestMutation<CasinoState>('blackjack:start', '/api/blackjack/start', { bet }),
  blackjackAction: (action: BlackjackAction) =>
    requestMutation<CasinoState>(`blackjack:${action}`, '/api/blackjack/action', { action }),
  refill: () => requestMutation<{ balance: number }>('refill', '/api/refill', {}),
}

export function stopBackend(): void {
  void backendChild?.kill()
  backendChild = undefined
  backendStartup = undefined
}

export type { RouletteChoice }
