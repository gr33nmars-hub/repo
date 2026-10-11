import assert from 'node:assert/strict'
import test from 'node:test'
import { decodeApiResponse } from '../src/lib/apiResponse.mjs'
import { RequestTimeoutError, withRequestTimeout } from '../src/lib/requestTimeout.mjs'

test('API response decoder preserves valid JSON bodies and safe HTTP errors', async () => {
  assert.deepEqual(await decodeApiResponse(new Response('{"ok":true}', {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })), { kind: 'success', body: { ok: true } })
  assert.deepEqual(await decodeApiResponse(new Response('{"detail":"bad bet","code":"invalid_bet"}', {
    status: 422,
    headers: { 'Content-Type': 'application/json' },
  })), {
    kind: 'http-error', status: 422, message: 'bad bet', code: 'invalid_bet',
  })
})

test('API response decoder reports malformed JSON without throwing', async () => {
  assert.deepEqual(await decodeApiResponse(new Response('not-json', { status: 502 })), {
    kind: 'invalid-json',
  })
})

test('request timeout aborts work and reports a typed timeout', async () => {
  let aborted = false
  await assert.rejects(withRequestTimeout((signal) => new Promise((resolve) => {
    signal.addEventListener('abort', () => { aborted = true; resolve() }, { once: true })
  }), 5), RequestTimeoutError)
  assert.equal(aborted, true)
})
