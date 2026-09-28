export interface CloseRequestEvent {
  preventDefault(): void
}

export function createCloseRequestHandler(
  stopBackend: () => Promise<void>,
  destroyWindow: () => Promise<void>,
  reportError?: (error: unknown) => void,
): (event: CloseRequestEvent) => Promise<void>
