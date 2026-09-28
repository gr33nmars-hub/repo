import assert from 'node:assert/strict'
import test from 'node:test'
import { createCloseRequestHandler } from '../src/platform/desktopLifecycle.mjs'

function createCloseEvent() {
  return {
    prevented: false,
    preventDefault() {
      this.prevented = true
    },
  }
}

test('close request waits for backend shutdown before destroying the window', async () => {
  const order = []
  let finishShutdown
  const shutdown = new Promise((resolve) => { finishShutdown = resolve })
  const handleClose = createCloseRequestHandler(
    async () => {
      order.push('stop-started')
      await shutdown
      order.push('stop-finished')
    },
    async () => { order.push('destroyed') },
  )
  const event = createCloseEvent()

  const closing = handleClose(event)
  await Promise.resolve()

  assert.equal(event.prevented, true)
  assert.deepEqual(order, ['stop-started'])
  finishShutdown()
  await closing
  assert.deepEqual(order, ['stop-started', 'stop-finished', 'destroyed'])
})

test('repeated close requests share one shutdown and destroy operation', async () => {
  let finishShutdown
  const shutdown = new Promise((resolve) => { finishShutdown = resolve })
  let stopCount = 0
  let destroyCount = 0
  const handleClose = createCloseRequestHandler(
    async () => {
      stopCount += 1
      await shutdown
    },
    async () => { destroyCount += 1 },
  )
  const firstEvent = createCloseEvent()
  const secondEvent = createCloseEvent()

  const firstClose = handleClose(firstEvent)
  const secondClose = handleClose(secondEvent)
  assert.equal(firstClose, secondClose)
  assert.equal(firstEvent.prevented, true)
  assert.equal(secondEvent.prevented, true)
  finishShutdown()
  await Promise.all([firstClose, secondClose])

  assert.equal(stopCount, 1)
  assert.equal(destroyCount, 1)
})

test('window still closes if backend shutdown reports an error', async () => {
  const shutdownError = new Error('sidecar shutdown failed')
  const reported = []
  let destroyCount = 0
  const handleClose = createCloseRequestHandler(
    async () => { throw shutdownError },
    async () => { destroyCount += 1 },
    (error) => reported.push(error),
  )

  await handleClose(createCloseEvent())

  assert.deepEqual(reported, [shutdownError])
  assert.equal(destroyCount, 1)
})
