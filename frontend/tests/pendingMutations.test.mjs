import assert from 'node:assert/strict'
import test from 'node:test'
import { createPendingMutationStore } from '../src/lib/pendingMutations.mjs'

function memoryStorage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}

test('pending key and exact request body survive a new store instance', () => {
  const storage = memoryStorage()
  const first = createPendingMutationStore('pending', () => storage)
  const saved = {
    'blackjack:hit': {
      key: 'request-1',
      payload: JSON.stringify({ path: '/api/blackjack/action', payload: { action: 'hit' } }),
    },
  }
  first.write(saved)

  const afterReload = createPendingMutationStore('pending', () => storage)
  assert.deepEqual(afterReload.read(), saved)
})

test('blocked browser storage retains the pending request in memory', () => {
  const blockedStorage = () => { throw new Error('storage disabled') }
  const store = createPendingMutationStore('pending', blockedStorage)
  const saved = { 'play:slots': { key: 'request-2', payload: '{"bet":10}' } }
  store.write(saved)

  assert.deepEqual(store.read(), saved)
  assert.deepEqual(createPendingMutationStore('pending', blockedStorage).read(), {})
})

test('malformed persisted values do not replace the live pending state', () => {
  const storage = memoryStorage()
  storage.setItem('pending', '{broken')
  const store = createPendingMutationStore('pending', () => storage)
  const saved = { refill: { key: 'request-3', payload: '{}' } }
  store.write(saved)

  assert.deepEqual(store.read(), saved)
})
