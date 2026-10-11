export async function decodeApiResponse(response) {
  let body
  try {
    body = await response.json()
  } catch {
    return { kind: 'invalid-json' }
  }

  if (!response.ok) {
    const record = body && typeof body === 'object' && !Array.isArray(body) ? body : {}
    return {
      kind: 'http-error',
      status: response.status,
      message: typeof record.detail === 'string' ? record.detail : `Запрос не прошёл (HTTP ${response.status})`,
      code: typeof record.code === 'string' ? record.code : undefined,
    }
  }

  return { kind: 'success', body }
}
