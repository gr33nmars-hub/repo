export type DecodedApiResponse<T = unknown> =
  | { kind: 'success'; body: T }
  | { kind: 'invalid-json' }
  | { kind: 'http-error'; status: number; message: string; code?: string }

export function decodeApiResponse(response: Response): Promise<DecodedApiResponse>
