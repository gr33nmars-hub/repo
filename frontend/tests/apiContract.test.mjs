import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const [contract, types] = await Promise.all([
  readFile(new URL('../../backend/tests/fixtures/api-contract-v1.json', import.meta.url), 'utf8'),
  readFile(new URL('../src/types.ts', import.meta.url), 'utf8'),
])

test('frontend RoundResult retains every backend roulette response field', () => {
  const fields = JSON.parse(contract).roulette_play.result
  const interfaceBody = types.match(/export interface RoundResult \{([\s\S]*?)\n\}/)?.[1]
  assert.ok(interfaceBody)
  for (const field of fields) {
    assert.match(interfaceBody, new RegExp(`^\\s*${field}\\??:`, 'm'), field)
  }
})
