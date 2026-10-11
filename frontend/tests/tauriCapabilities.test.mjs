import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const capabilities = JSON.parse(
  await readFile(new URL('../src-tauri/capabilities/default.json', import.meta.url), 'utf8'),
)

test('desktop capability allows graceful sidecar shutdown and window destruction', () => {
  const permissionIds = capabilities.permissions.map((permission) =>
    typeof permission === 'string' ? permission : permission.identifier,
  )
  assert.ok(!permissionIds.includes('core:default'))
  assert.ok(capabilities.permissions.includes('core:event:allow-listen'))
  assert.ok(capabilities.permissions.includes('core:event:allow-unlisten'))
  assert.ok(capabilities.permissions.includes('core:window:allow-destroy'))
  assert.ok(capabilities.permissions.includes('shell:allow-kill'))
  assert.ok(!permissionIds.some((permission) => permission.startsWith('fs:')))
  assert.ok(!permissionIds.some((permission) => permission.startsWith('dialog:')))
  assert.ok(
    capabilities.permissions.some(
      (permission) =>
        typeof permission === 'object' &&
        permission.identifier === 'shell:allow-spawn' &&
        permission.allow.some(
          (command) =>
            command.name === 'binaries/noir-api' &&
            command.sidecar &&
            Array.isArray(command.args) &&
            command.args.length === 0,
        ),
    ),
  )
})
