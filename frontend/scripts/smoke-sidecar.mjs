import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, rm } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

if (process.platform !== 'win32') {
  throw new Error('The packaged sidecar smoke check requires Windows.')
}

const executable = fileURLToPath(
  new URL('../src-tauri/binaries/astoria-api-x86_64-pc-windows-msvc.exe', import.meta.url),
)
const workDir = await mkdtemp(join(tmpdir(), 'astoria-casino-sidecar-'))
const port = await reservePort()
const savePath = join(workDir, 'casino.sqlite3')
let sidecar

try {
  const baseUrl = `http://127.0.0.1:${port}`
  sidecar = await startSidecar(savePath, port)
  await waitForSidecar(baseUrl, sidecar.token, sidecar.nonce, sidecar.child)

  const unauthorized = await fetch(`${baseUrl}/api/state`)
  assert.equal(unauthorized.status, 401, 'state endpoint must require the sidecar token')

  const headers = { 'X-Astoria-Api-Token': sidecar.token }
  const initialResponse = await fetch(`${baseUrl}/api/state`, { headers })
  assert.equal(initialResponse.status, 200)
  const initialState = await initialResponse.json()
  assert.equal(initialState.player.balance, 2500)

  const request = {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ bet: 10, choice: 'red', idempotency_key: 'sidecar-smoke-round' }),
  }
  const firstResponse = await fetch(`${baseUrl}/api/games/roulette/play`, request)
  assert.equal(firstResponse.status, 200)
  const firstResult = await firstResponse.json()
  const retryResponse = await fetch(`${baseUrl}/api/games/roulette/play`, request)
  assert.equal(retryResponse.status, 200)
  assert.deepEqual(await retryResponse.json(), firstResult, 'retry must return the committed response')
  assert.equal(
    firstResult.state.player.balance,
    initialState.player.balance - firstResult.result.bet + firstResult.result.payout,
  )

  await stopSidecar(baseUrl, sidecar.token, sidecar.closed)

  sidecar = await startSidecar(savePath, port)
  await waitForSidecar(baseUrl, sidecar.token, sidecar.nonce, sidecar.child)
  const restartedHeaders = { 'X-Astoria-Api-Token': sidecar.token }
  const restoredResponse = await fetch(`${baseUrl}/api/state`, { headers: restartedHeaders })
  assert.equal(restoredResponse.status, 200)
  const restoredState = await restoredResponse.json()
  assert.equal(restoredState.player.balance, firstResult.state.player.balance)
  assert.equal(restoredState.player.rounds_played, 1)
  assert.deepEqual(restoredState.history[0], {
    ...firstResult.result,
    verification_status: 'verified',
  })

  const replayResponse = await fetch(`${baseUrl}/api/games/roulette/play`, {
    ...request,
    headers: { ...restartedHeaders, 'Content-Type': 'application/json' },
  })
  assert.equal(replayResponse.status, 200)
  assert.deepEqual(await replayResponse.json(), firstResult, 'retry must survive a sidecar restart')
  await stopSidecar(baseUrl, sidecar.token, sidecar.closed)
  console.log('Packaged sidecar smoke passed: auth, settlement, persistence, idempotent retry across restart, shutdown.')
} finally {
  if (sidecar?.child.exitCode === null && sidecar.child.signalCode === null) {
    try {
      await fetch(`http://127.0.0.1:${port}/api/shutdown`, {
        method: 'POST',
        headers: { 'X-Astoria-Api-Token': sidecar.token },
        signal: AbortSignal.timeout(1000),
      })
    } catch {
      sidecar.child.kill()
    }
    await Promise.race([sidecar.closed, delay(5000)])
  }
  if (workDir.startsWith(tmpdir()) && workDir.includes('astoria-casino-sidecar-')) {
    try {
      await rm(workDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 250 })
    } catch (error) {
      console.error(`Could not remove temporary sidecar data at ${workDir}:`, error)
    }
  }
}

async function startSidecar(savePath, sidecarPort) {
  const token = crypto.randomUUID() + crypto.randomUUID()
  const nonce = crypto.randomUUID()
  const child = spawn(executable, [], {
    env: {
      ...process.env,
      ASTORIA_CASINO_API_INSTANCE_NONCE: nonce,
      ASTORIA_CASINO_API_PORT: String(sidecarPort),
      ASTORIA_CASINO_API_TOKEN: token,
      ASTORIA_CASINO_SAVE_PATH: savePath,
    },
    stdio: 'ignore',
    windowsHide: true,
  })
  const started = new Promise((resolve, reject) => {
    child.once('spawn', resolve)
    child.once('error', reject)
  })
  const closed = new Promise((resolve) =>
    child.once('close', (code, signal) => resolve({ code, signal })),
  )
  await started
  return { child, closed, nonce, token }
}

async function stopSidecar(baseUrl, token, closed) {
  const response = await fetch(`${baseUrl}/api/shutdown`, {
    method: 'POST',
    headers: { 'X-Astoria-Api-Token': token },
  })
  assert.equal(response.status, 200)
  let timeout
  const exit = await Promise.race([
    closed,
    new Promise((_, reject) => {
      timeout = setTimeout(() => reject(new Error('Sidecar did not exit')), 5000)
    }),
  ]).finally(() => clearTimeout(timeout))
  assert.equal(exit.code, 0, `sidecar exited with ${exit.signal ?? exit.code}`)
}

async function reservePort() {
  const server = createServer()
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  assert.ok(address && typeof address !== 'string')
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()))
  return address.port
}

async function waitForSidecar(baseUrl, apiToken, expectedNonce, process) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (process.exitCode !== null || process.signalCode !== null) {
      throw new Error(`Sidecar exited before startup (${process.signalCode ?? process.exitCode})`)
    }
    try {
      const response = await fetch(`${baseUrl}/api/health`, {
        headers: { 'X-Astoria-Api-Token': apiToken },
        signal: AbortSignal.timeout(1000),
      })
      if (response.ok) {
        const health = await response.json()
        if (health.status === 'ok' && health.instance_nonce === expectedNonce) return
      }
    } catch {
      // The bundled process may need a few seconds to initialize its database.
    }
    await delay(250)
  }
  throw new Error('Packaged sidecar did not become healthy within 20 seconds.')
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}
