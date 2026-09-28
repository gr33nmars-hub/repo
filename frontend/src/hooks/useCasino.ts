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
  const [lastRound, setLastRound] = useState<string | null>(null)
  const retryOperation = useRef<(() => Promise<void>) | null>(null)

  const refresh = useCallback(async () => {
    try {
      setState(await casinoApi.state())
      const pending = hasPendingMutation()
      setRetryAvailable(pending)
      setError(pending
        ? 'Есть запрос без подтверждённого результата. Повтори его, чтобы уточнить исход.'
        : null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить казино')
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- asynchronous API hydration
    void refresh()
  }, [refresh])

  const handleMutationFailure = (
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
  }

  const act = useCallback(async function runStateOperation(operation: () => Promise<CasinoState>, notice?: string) {
    setBusy(true)
    setError(null)
    try {
      const next = await operation()
      setState(next)
      if (notice) setLastRound(notice)
      retryOperation.current = null
      setRetryAvailable(false)
      return true
    } catch (caught) {
      handleMutationFailure(
        caught,
        'Не удалось выполнить действие',
        async () => { await runStateOperation(operation, notice) },
      )
      return false
    } finally {
      setBusy(false)
    }
  }, [])

  const play = useCallback(async function runGame(
    game: Exclude<GameId, 'blackjack'>,
    bet: number,
    choice = '',
    expectedServerSeedHash?: string,
  ) {
    setBusy(true)
    setError(null)
    try {
      const response = await casinoApi.play(game, bet, choice, expectedServerSeedHash)
      setState(response.state)
      setLastRound(response.result.message)
      retryOperation.current = null
      setRetryAvailable(false)
      return response.result
    } catch (caught) {
      handleMutationFailure(
        caught,
        'Раунд не запустился',
        async () => { await runGame(game, bet, choice, expectedServerSeedHash) },
      )
      return null
    } finally {
      setBusy(false)
    }
  }, [])

  const startBlackjack = useCallback((bet: number) =>
    act(() => casinoApi.startBlackjack(bet), 'Карты розданы'), [act])

  const blackjackAction = useCallback((action: BlackjackAction) =>
    act(() => casinoApi.blackjackAction(action)), [act])

  const refill = useCallback(async function runRefill() {
    setBusy(true)
    setError(null)
    try {
      const { balance } = await casinoApi.refill()
      setState((current) => current ? { ...current, player: { ...current.player, balance } } : current)
      setLastRound('Баланс пополнен')
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
      setBusy(false)
    }
  }, [])

  const retry = useCallback(async () => {
    const operation = retryOperation.current
    if (operation) await operation()
    else {
      let retryError: string | undefined
      try {
        await retryPendingMutation()
      } catch (caught) {
        const reconciled = reconciledConflictState(caught)
        if (reconciled) {
          setState(reconciled)
          retryError = 'Состояние обновлено. Проверь игру и повтори действие при необходимости.'
        } else {
          retryError = caught instanceof Error ? caught.message : 'Не удалось повторить запрос'
        }
      }
      await refresh()
      if (retryError) setError(retryError)
    }
  }, [refresh])

  return {
    state,
    busy,
    error,
    retryAvailable,
    lastRound,
    refresh,
    retry,
    play,
    startBlackjack,
    blackjackAction,
    refill,
    clearNotice: () => setLastRound(null),
    clearError: () => setError(null),
  }
}

export type { RouletteChoice }
