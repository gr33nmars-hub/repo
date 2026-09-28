import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const capabilities = JSON.parse(
  await readFile(new URL('../src-tauri/capabilities/default.json', import.meta.url), 'utf8'),
)

test('desktop capability allows graceful sidecar shutdown and window destruction', () => {
  assert.ok(capabilities.permissions.includes('core:window:allow-destroy'))
  assert.ok(capabilities.permissions.includes('shell:allow-kill'))
  assert.ok(
    capabilities.permissions.some(
      (permission) =>
        typeof permission === 'object' &&
        permission.identifier === 'shell:allow-spawn' &&
        permission.allow.some((command) => command.name === 'binaries/noir-api' && command.sidecar),
    ),
  )
})
