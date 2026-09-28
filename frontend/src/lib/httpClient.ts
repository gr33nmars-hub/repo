import type { CasinoState } from '../types'
import { apiBase } from './apiConfig'
import { apiHeaders, prepareBackend } from '../platform/desktopBackend'

export class CasinoApiError extends Error {
  readonly status: number
  readonly reconciledState?: CasinoState
  readonly code?: string

  constructor(message: string, status: number, reconciledState?: CasinoState, code?: string) {
    super(message)
    this.name = 'CasinoApiError'
    this.status = status
    this.reconciledState = reconciledState
    this.code = code
  }
}

export async function requestApi<T>(path: string, init?: RequestInit): Promise<T> {
  await prepareBackend()
  let response: Response
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...apiHeaders(), ...init?.headers },
    })
  } catch {
    throw new Error('Нет связи с игрой. Проверь соединение и повтори попытку.')
  }
  const body = await response.json()
  if (!response.ok) {
    throw new CasinoApiError(body.detail ?? 'Запрос не прошёл', response.status, undefined, body.code)
  }
  return body as T
}
