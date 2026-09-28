import { isTauri } from '@tauri-apps/api/core'
import { Command, type Child } from '@tauri-apps/plugin-shell'
import { apiBase } from '../lib/apiConfig'

const API_TOKEN_ENV = 'NOIR_CASINO_API_TOKEN'
const API_TOKEN_HEADER = 'X-Noir-Api-Token'
const API_INSTANCE_NONCE_ENV = 'NOIR_CASINO_API_INSTANCE_NONCE'
const SHUTDOWN_TIMEOUT_MS = 3000

let backendChild: Child | undefined
let backendStartup: Promise<void> | undefined
let backendToken: string | undefined
let backendGeneration = 0
let backendExit: Promise<void> | undefined
let resolveBackendExit: (() => void) | undefined

function createBackendToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32))
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export function apiHeaders(): Record<string, string> {
  return backendToken ? { [API_TOKEN_HEADER]: backendToken } : {}
}

async function waitForBackend(
  expectedNonce?: string,
  isCurrent: () => boolean = () => true,
): Promise<void> {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (!isCurrent()) throw new Error('Запуск игры отменён.')
    let response: Response | undefined
    try {
      response = await fetch(`${apiBase}/api/health`, { headers: apiHeaders() })
    } catch {
      // Keep waiting while the bundled backend starts.
    }
    if (response?.ok) {
      try {
        const health = await response.json()
        if (health.status === 'ok' && (!expectedNonce || health.instance_nonce === expectedNonce)) return
      } catch {
        // A response without the expected health payload is not our backend.
      }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 250))
  }
  if (!isCurrent()) throw new Error('Запуск игры отменён.')
  throw new Error('Не удалось запустить игру. Перезапусти приложение.')
}

export async function prepareBackend(): Promise<void> {
  if (!isTauri() || import.meta.env.DEV) {
    if (import.meta.env.DEV) {
      const startup = backendStartup ??= waitForBackend()
      try {
        await startup
      } catch (error) {
        if (backendStartup === startup) backendStartup = undefined
        throw error
      }
    }
    return
  }
  const generation = backendGeneration
  const startup = backendStartup ??= (async () => {
    const token = createBackendToken()
    const nonce = createBackendToken()
    backendToken = token

    const command = Command.sidecar('binaries/noir-api', [], {
      env: { [API_TOKEN_ENV]: token, [API_INSTANCE_NONCE_ENV]: nonce },
    })
    let child: Child | undefined
    backendExit = new Promise<void>((resolve) => { resolveBackendExit = resolve })
    const resetAfterExit = () => {
      resolveBackendExit?.()
      resolveBackendExit = undefined
      backendExit = undefined
      if (!child || backendChild !== child) return
      backendChild = undefined
      backendStartup = undefined
      backendToken = undefined
    }
    command.on('close', resetAfterExit)
    command.on('error', resetAfterExit)
    child = await command.spawn()
    if (generation !== backendGeneration) {
      await child.kill().catch(() => undefined)
      throw new Error('Запуск игры отменён.')
    }
    backendChild = child
    await waitForBackend(nonce, () => generation === backendGeneration)
    if (generation !== backendGeneration) throw new Error('Запуск игры отменён.')
  })()

  try {
    await startup
  } catch (error) {
    if (backendStartup === startup) {
      const child = backendChild
      backendChild = undefined
      backendStartup = undefined
      backendToken = undefined
      if (child) void child.kill().catch(() => undefined)
    }
    throw error
  }
}

export async function stopBackend(): Promise<void> {
  backendGeneration += 1
  const child = backendChild
  const token = backendToken
  const exited = backendExit
  backendChild = undefined
  backendToken = undefined
  backendStartup = undefined
  if (!child) return

  let shutdownAccepted = false
  if (token) {
    const controller = new AbortController()
    const timeout = globalThis.setTimeout(() => controller.abort(), 1000)
    try {
      const response = await fetch(`${apiBase}/api/shutdown`, {
        method: 'POST',
        headers: { [API_TOKEN_HEADER]: token },
        signal: controller.signal,
      })
      shutdownAccepted = response.ok
    } catch {
      // Fall back to the shell process handle if graceful shutdown is unavailable.
    } finally {
      globalThis.clearTimeout(timeout)
    }
  }

  if (shutdownAccepted && exited) {
    let timeout: ReturnType<typeof globalThis.setTimeout> | undefined
    await Promise.race([
      exited,
      new Promise<void>((resolve) => {
        timeout = globalThis.setTimeout(resolve, SHUTDOWN_TIMEOUT_MS)
      }),
    ])
    if (timeout !== undefined) globalThis.clearTimeout(timeout)
    if (!backendExit) return
  }

  await child.kill().catch(() => undefined)
}
