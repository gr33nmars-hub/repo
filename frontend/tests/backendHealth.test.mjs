import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import test from 'node:test'
import { waitForBackend } from '../src/platform/backendHealth.ts'

async function withHealthServer(handler, check) {
  const server = createServer(handler)
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  try {
    await check(`http://127.0.0.1:${server.address().port}/api/health`)
  } finally {
    server.closeAllConnections()
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()))
  }
}

test('backend readiness forwards authentication and accepts only an ok status', { timeout: 3000 }, async () => {
  let calls = 0
  await withHealthServer((request, response) => {
    calls++
    assert.equal(request.headers['x-astoria-api-token'], 'test-token')
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ status: calls === 1 ? 'starting' : 'ok' }))
  }, (url) => waitForBackend(url, { 'X-Astoria-Api-Token': 'test-token' }, 1500))
  assert.equal(calls, 2)
})

test('a health connection that never answers cannot hold startup past its deadline', { timeout: 3000 }, async () => {
  await withHealthServer(() => {}, async (url) => {
    await assert.rejects(waitForBackend(url, {}, 60), /Локальный сервер не запустился/)
  })
})

test('a health response with a stalled body is aborted and a later startup can recover', { timeout: 3000 }, async () => {
  let stalled = true
  await withHealthServer((_request, response) => {
    response.writeHead(200, { 'Content-Type': 'application/json' })
    if (stalled) {
      response.write('{"status":')
      return
    }
    response.end('{"status":"ok"}')
  }, async (url) => {
    await assert.rejects(waitForBackend(url, {}, 60), /Локальный сервер не запустился/)
    stalled = false
    await waitForBackend(url, {}, 1500)
  })
})
