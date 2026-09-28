export function createPendingMutationStore(storageKey, storageProvider = () => globalThis.localStorage) {
  let memory = {}
  let unsafe = false

  function read() {
    let stored
    try {
      stored = storageProvider()?.getItem(storageKey)
    } catch {
      return memory
    }
    if (stored === null || stored === undefined) return memory

    let value
    try {
      value = JSON.parse(stored)
    } catch {
      unsafe = true
      return memory
    }
    if (
      value && typeof value === 'object' && !Array.isArray(value)
      && Object.values(value).every((request) => (
        request && typeof request === 'object'
        && typeof request.key === 'string'
        && typeof request.payload === 'string'
      ))
    ) {
      unsafe = false
      return value
    }
    unsafe = true
    return memory
  }

  function isSafe() {
    return !unsafe
  }

  function write(value) {
    memory = value
    try {
      const storage = storageProvider()
      if (!storage) return false
      if (Object.keys(value).length) storage.setItem(storageKey, JSON.stringify(value))
      else storage.removeItem(storageKey)
      unsafe = false
      return true
    } catch {
      return false
    }
  }

  return { read, write, isSafe }
}
