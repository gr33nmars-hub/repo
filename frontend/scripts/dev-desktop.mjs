import { spawn } from 'node:child_process'

const root = new URL('..', import.meta.url)
const jobs = []
let stopping = false

function start(command, args, label) {
  const child = spawn(command, args, {
    cwd: root,
    stdio: 'inherit',
    env: process.env,
    shell: process.platform === 'win32',
  })
  child.on('error', (error) => {
    console.error(`[${label}] ${error.message}`)
    stop(1)
  })
  child.on('exit', (code) => {
    if (!stopping && code && code !== 0) stop(code)
  })
  jobs.push(child)
}

function stop(code = 0) {
  if (stopping) return
  stopping = true
  for (const child of jobs) {
    if (!child.killed) child.kill()
  }
  process.exitCode = code
  setTimeout(() => process.exit(code), 500)
}

process.on('SIGINT', () => stop(0))
process.on('SIGTERM', () => stop(0))
start('uv', ['run', '--directory', '..', 'python', 'backend/run_api.py'], 'api')
start('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], 'vite')
