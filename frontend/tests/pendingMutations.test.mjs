import assert from 'node:assert/strict'
import test from 'node:test'
import {
  createPendingMutationStore,
  handlePendingMutationFailure,
  sendWithPendingMutation,
} from '../src/lib/pendingMutations.mjs'
import { isAllowedMutation, isPendingMutationRecord } from '../src/lib/mutationContract.mjs'

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

test('unknown send result survives reload and retries the exact key, route, and body', async () => {
  const storage = memoryStorage()
  const active = {
    key: 'request-same-key',
    payload: JSON.stringify({
      path: '/api/games/roulette/play',
      payload: { bet: 25, choice: 'red', client_seed: 'client-1' },
    }),
  }
  let store = createPendingMutationStore('pending', () => storage)
  const persist = (request) => store.write({ 'play:roulette': request })
  const clear = (request) => {
    const latest = store.read()
    if (latest['play:roulette']?.key === request.key) delete latest['play:roulette']
    store.write(latest)
  }
  const firstRequest = JSON.parse(active.payload)
  await assert.rejects(sendWithPendingMutation({
    active,
    persist,
    send: async (request) => {
      assert.equal(request.key, active.key)
      assert.deepEqual(JSON.parse(request.payload), firstRequest)
      throw new Error('connection lost after send')
    },
    clear,
    persistenceError: () => new Error('persistence failed'),
  }), /connection lost/)

  store = createPendingMutationStore('pending', () => storage)
  const recovered = store.read()['play:roulette']
  assert.deepEqual(recovered, active)
  let replayed
  await sendWithPendingMutation({
    active: recovered,
    persist: (request) => store.write({ 'play:roulette': request }),
    send: async (request) => {
      replayed = { key: request.key, ...JSON.parse(request.payload) }
      return { ok: true }
    },
    clear,
    persistenceError: () => new Error('persistence failed'),
  })
  assert.deepEqual(replayed, {
    key: 'request-same-key',
    path: '/api/games/roulette/play',
    payload: { bet: 25, choice: 'red', client_seed: 'client-1' },
  })
  assert.deepEqual(store.read(), {})
})

test('409 reconciliation refreshes state, clears the matching pending key, and surfaces it', async () => {
  const state = { balance: 90 }
  const conflict = { status: 409, message: 'conflict', code: 'state_conflict' }
  let refreshed = false
  let cleared = false
  await assert.rejects(handlePendingMutationFailure(conflict, {
    fetchState: async () => { refreshed = true; return state },
    clearPending: async () => { cleared = true },
    isDefinitive: () => false,
    makeConflictError: (error, reconciledState) => ({
      status: error.status,
      reconciledState,
    }),
    hasReconciledState: (error) => Boolean(error.reconciledState),
  }), (error) => error.status === 409 && error.reconciledState === state)
  assert.equal(refreshed, true)
  assert.equal(cleared, true)
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

test('mutation contract permits only known operation and route pairs with valid payloads', () => {
  assert.equal(isAllowedMutation('play:roulette', '/api/games/roulette/play', {
    bet: 10,
    choice: 'red',
    client_seed: 'client-1',
  }), true)
  assert.equal(isAllowedMutation('play:roulette', '/api/shutdown', {}), false)
  assert.equal(isAllowedMutation('blackjack:hit', '/api/blackjack/action', { action: 'stand' }), false)
  assert.equal(isAllowedMutation('play:slots', '/api/games/slots/play', {
    bet: 10,
    choice: '',
    client_seed: 'client-1',
    extra: true,
  }), false)
})

test('persisted mutation record requires a known route, matching operation, and backend key size', () => {
  const pending = {
    key: 'request-1',
    payload: JSON.stringify({
      path: '/api/blackjack/action',
      payload: { action: 'hit' },
    }),
  }
  assert.equal(isPendingMutationRecord('blackjack:hit', pending), true)
  assert.equal(isPendingMutationRecord('blackjack:stand', pending), false)
  assert.equal(isPendingMutationRecord('blackjack:hit', { ...pending, key: '' }), false)
  assert.equal(isPendingMutationRecord('blackjack:hit', { ...pending, key: 'k'.repeat(129) }), false)
})
