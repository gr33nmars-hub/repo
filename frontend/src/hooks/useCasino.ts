import { useCallback, useEffect, useRef, useState } from 'react'
import { casinoApi } from '../lib/casino.api'
import {
  hasPendingMutation,
  isDefinitiveMutationRejection,
  isPendingMutationBlock,
  reconciledConflictState,
  retryPendingMutation,
} from '../lib/casino.commands'
import type { BlackjackAction, CasinoState, GameId, RouletteChoice } from '../types'

export function useCasino() {
  const [state, setState] = useState<CasinoState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryAvailable, setRetryAvailable] = useState(false)
  const retryOperation = useRef<(() => Promise<void>) | null>(null)
  const operationRunning = useRef(false)

  const beginOperation = useCallback(() => {
    if (operationRunning.current) return false
    operationRunning.current = true
    setBusy(true)
    return true
  }, [])

  const finishOperation = useCallback(() => {
    operationRunning.current = false
    setBusy(false)
  }, [])

  const loadState = useCallback(async () => {
    try {
      setState(await casinoApi.state())
      const pending = hasPendingMutation()
      setRetryAvailable(pending)
      setError(pending
        ? 'Есть запрос без подтверждённого результата. Повтори его, чтобы уточнить исход.'
        : null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить игру.')
    }
  }, [])

  const refresh = useCallback(async () => {
    if (!beginOperation()) return
    try {
      await loadState()
    } finally {
      finishOperation()
    }
  }, [beginOperation, finishOperation, loadState])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh()
  }, [refresh])

  const handleMutationFailure = useCallback((
    caught: unknown,
    fallback: string,
    retry: () => Promise<void>,
    conflictMessage = 'Состояние обновлено. Проверь стол и повтори действие при необходимости.',
  ) => {
    const reconciled = reconciledConflictState(caught)
    if (reconciled) {
      setState(reconciled)
      retryOperation.current = null
      setRetryAvailable(false)
      setError(conflictMessage)
      return
    }
    retryOperation.current = isPendingMutationBlock(caught) || isDefinitiveMutationRejection(caught)
      ? null
      : retry
    setRetryAvailable(retryOperation.current !== null || hasPendingMutation())
    setError(caught instanceof Error ? caught.message : fallback)
  }, [])

  const act = useCallback(async function runStateOperation(operation: () => Promise<CasinoState>) {
    if (!beginOperation()) return false
    setError(null)
    try {
      const next = await operation()
      const current = await casinoApi.state().catch(() => next)
      setState(current)
      retryOperation.current = null
      setRetryAvailable(false)
      return true
    } catch (caught) {
      handleMutationFailure(
        caught,
        'Не удалось выполнить действие',
        async () => { await runStateOperation(operation) },
      )
      return false
    } finally {
      finishOperation()
    }
  }, [beginOperation, finishOperation, handleMutationFailure])

  const play = useCallback(async function runGame(
    game: Exclude<GameId, 'blackjack'>,
    bet: number,
    choice = '',
    expectedServerSeedHash?: string,
  ) {
    if (!beginOperation()) return null
    setError(null)
    try {
      const response = await casinoApi.play(game, bet, choice, expectedServerSeedHash)
      const current = await casinoApi.state().catch(() => response.state)
      setState(current)
      retryOperation.current = null
      setRetryAvailable(false)
      return current.history.find((round) => (
        round.game_id === response.result.game_id && round.played_at === response.result.played_at
      )) ?? response.result
    } catch (caught) {
      handleMutationFailure(
        caught,
        'Не удалось начать раунд.',
        async () => { await runGame(game, bet, choice, expectedServerSeedHash) },
      )
      return null
    } finally {
      finishOperation()
    }
  }, [beginOperation, finishOperation, handleMutationFailure])

  const startBlackjack = useCallback((bet: number, expectedHash?: string) =>
    act(() => casinoApi.startBlackjack(bet, expectedHash)), [act])

  const blackjackAction = useCallback((action: BlackjackAction) =>
    act(() => casinoApi.blackjackAction(action)), [act])

  const refill = useCallback(async function runRefill() {
    if (!beginOperation()) return false
    setError(null)
    try {
      const { balance } = await casinoApi.refill()
      const current = await casinoApi.state().catch(() => null)
      setState(current ?? ((previous) => previous
        ? { ...previous, player: { ...previous.player, balance } }
        : previous))
      retryOperation.current = null
      setRetryAvailable(false)
      return true
    } catch (caught) {
      handleMutationFailure(
        caught,
        'Не удалось пополнить баланс',
        async () => { await runRefill() },
        'Состояние обновлено. Проверь баланс и повтори действие при необходимости.',
      )
      return false
    } finally {
      finishOperation()
    }
  }, [beginOperation, finishOperation, handleMutationFailure])

  const retry = useCallback(async () => {
    const operation = retryOperation.current
    if (operation) await operation()
    else {
      if (!beginOperation()) return
      try {
        let retryError: string | undefined
        try {
          await retryPendingMutation()
        } catch (caught) {
          const reconciled = reconciledConflictState(caught)
          if (reconciled) {
            setState(reconciled)
            retryError = 'Состояние обновлено. Проверь игру и повтори действие при необходимости.'
          } else {
            retryError = caught instanceof Error ? caught.message : 'Не удалось повторить запрос.'
          }
        }
        await loadState()
        if (retryError) setError(retryError)
      } finally {
        finishOperation()
      }
    }
  }, [beginOperation, finishOperation, loadState])

  return {
    state,
    busy,
    error,
    retryAvailable,
    refresh,
    retry,
    play,
    startBlackjack,
    blackjackAction,
    refill,
    clearError: () => setError(null),
  }
}

export type { RouletteChoice }
