import { isTauri } from '@tauri-apps/api/core'
import type { Child } from '@tauri-apps/plugin-shell'
import { apiBase } from '../lib/apiConfig'
import { waitForBackend } from './backendHealth'

const API_TOKEN_HEADER = 'X-Astoria-Api-Token'
let apiToken: string | undefined = import.meta.env.VITE_CASINO_API_TOKEN

let backendStartup: Promise<void> | undefined
let backendProcess: Child | undefined

export function apiHeaders(): Record<string, string> {
  return apiToken ? { [API_TOKEN_HEADER]: apiToken } : {}
}

function createApiToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32))
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function startSidecar(): Promise<void> {
  if (!isTauri() || !import.meta.env.PROD || backendProcess) return

  const { Command } = await import('@tauri-apps/plugin-shell')
  apiToken = createApiToken()
  const command = Command.sidecar('binaries/astoria-api', [], {
    env: { ASTORIA_CASINO_API_TOKEN: apiToken },
  })
  command.on('close', () => {
    backendProcess = undefined
    backendStartup = undefined
  })
  command.on('error', () => {
    backendProcess = undefined
    backendStartup = undefined
  })
  const child = await command.spawn()
  backendProcess = child
  window.addEventListener(
    'beforeunload',
    () => {
      void child.kill().catch(() => undefined)
    },
    { once: true },
  )
}

export function prepareBackend(): Promise<void> {
  backendStartup ??= startSidecar()
    .then(() => waitForBackend(`${apiBase}/api/health`, apiHeaders()))
    .catch((error: unknown) => {
      backendStartup = undefined
      throw error
    })
  return backendStartup
}
