import type { CasinoState } from '../types'
import { apiBase } from './apiConfig'
import { apiHeaders, prepareBackend } from '../platform/desktopBackend'
import { decodeApiResponse } from './apiResponse.mjs'
import { RequestTimeoutError, withRequestTimeout } from './requestTimeout.mjs'

const REQUEST_TIMEOUT_MS = 15_000

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
  try {
    return await withRequestTimeout(async (signal) => {
      await prepareBackend()
      const response = await fetch(`${apiBase}${path}`, {
        ...init,
        signal,
        headers: { 'Content-Type': 'application/json', ...apiHeaders(), ...init?.headers },
      })
      const decoded = await decodeApiResponse(response)
      if (decoded.kind === 'invalid-json') {
        throw new CasinoApiError(
          `Сервер вернул некорректный ответ (HTTP ${response.status})`,
          response.status,
          undefined,
          'invalid_response',
        )
      }
      if (decoded.kind === 'http-error') {
        throw new CasinoApiError(decoded.message, decoded.status, undefined, decoded.code)
      }
      return decoded.body as T
    }, REQUEST_TIMEOUT_MS, init?.signal)
  } catch (caught) {
    if (caught instanceof CasinoApiError) throw caught
    if (caught instanceof RequestTimeoutError) {
      throw new Error('Игра не ответила вовремя. Исход запроса неизвестен; повтори тот же запрос.')
    }
    if (init?.signal?.aborted) throw caught
    throw new Error('Нет связи с игрой. Исход запроса неизвестен; повтори тот же запрос.')
  }
}
