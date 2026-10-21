export type DecodedApiResponse<T = unknown> =
  | { kind: 'success'; body: T }
  | { kind: 'invalid-json' }
  | { kind: 'http-error'; status: number; message: string; code?: string }

export async function decodeApiResponse(response: Response): Promise<DecodedApiResponse> {
  let body: unknown
  try {
    body = await response.json()
  } catch {
    return { kind: 'invalid-json' }
  }

  if (!response.ok) {
    const record = body && typeof body === 'object' && !Array.isArray(body)
      ? (body as Record<string, unknown>)
      : {}
    return {
      kind: 'http-error',
      status: response.status,
      message: typeof record.detail === 'string' ? record.detail : `Ошибка запроса (HTTP ${response.status})`,
      code: typeof record.code === 'string' ? record.code : undefined,
    }
  }

  return { kind: 'success', body }
}
