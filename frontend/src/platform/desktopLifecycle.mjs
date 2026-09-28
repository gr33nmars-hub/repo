export function createCloseRequestHandler(
  stopBackend,
  destroyWindow,
  reportError = (error) => console.error('Не удалось полностью остановить backend перед закрытием.', error),
) {
  let closePromise

  return (event) => {
    event.preventDefault()
    closePromise ??= (async () => {
      try {
        await stopBackend()
      } catch (error) {
        reportError(error)
      }
      await destroyWindow()
    })()
    return closePromise
  }
}
