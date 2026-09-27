export function createPendingMutationStore(storageKey, storageProvider = () => globalThis.localStorage) {
  let memory = {}

  function read() {
    try {
      const storage = storageProvider()
      const stored = storage?.getItem(storageKey)
      if (stored === null || stored === undefined) return memory
      const value = JSON.parse(stored)
      if (!value || typeof value !== 'object' || Array.isArray(value)) return memory
      if (Object.values(value).every((request) => (
        request && typeof request === 'object'
        && typeof request.key === 'string'
        && typeof request.payload === 'string'
      ))) return value
    } catch {
      // A volatile copy keeps retries available for the life of this page.
    }
    return memory
  }

  function write(value) {
    memory = value
    try {
      const storage = storageProvider()
      if (!storage) return
      if (Object.keys(value).length) storage.setItem(storageKey, JSON.stringify(value))
      else storage.removeItem(storageKey)
    } catch {
      // In-memory state remains usable if persistent browser storage is unavailable.
    }
  }

  return { read, write }
}
