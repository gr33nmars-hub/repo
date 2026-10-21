import { randomBytes } from 'node:crypto'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const frontendRoot = fileURLToPath(new URL('..', import.meta.url))
const processes = []
const apiToken = randomBytes(32).toString('hex')
const environment = {
  ...process.env,
  ASTORIA_CASINO_API_TOKEN: apiToken,
  VITE_CASINO_API_TOKEN: apiToken,
}

let stopping = false

function start(command, args, label) {
  const child = spawn(command, args, {
    cwd: frontendRoot,
    env: environment,
    stdio: 'inherit',
    windowsHide: true,
  })
  child.on('error', (error) => {
    console.error(`[${label}] ${error.message}`)
    stop(1)
  })
  child.on('exit', (code) => {
    if (!stopping) stop(code ?? 1)
  })
  processes.push(child)
  return child
}

function stop(code = 0) {
  if (stopping) return
  stopping = true
  process.exitCode = code
  void stopChildren()
}

async function stopChildren() {
  try {
    await fetch('http://127.0.0.1:8765/api/shutdown', {
      method: 'POST',
      headers: { 'X-Astoria-Api-Token': apiToken },
      signal: AbortSignal.timeout(1000),
    })
  } catch {
    // The API may already be stopped.
  }
  for (const child of processes) {
    if (child.exitCode === null && child.signalCode === null) child.kill()
  }
}

process.on('SIGINT', () => stop(0))
process.on('SIGTERM', () => stop(0))

start(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], 'vite')
start('uv', ['run', '--directory', '..', 'python', 'backend/run_api.py'], 'api')
