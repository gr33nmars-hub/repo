import { useCallback, useEffect, useRef, useState } from 'react'
import {
  casinoApi,
  isPendingMutationBlock,
  reconciledConflictState,
  retryPendingMutation,
} from '../lib/casino.api'
import type { BlackjackAction, CasinoState, GameId, RouletteChoice } from '../types'

export function useCasino() {
  const [state, setState] = useState<CasinoState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRound, setLastRound] = useState<string | null>(null)
  const retryOperation = useRef<(() => Promise<void>) | null>(null)

  const refresh = useCallback(async () => {
    try {
      setState(await casinoApi.state())
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось загрузить казино')
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- asynchronous API hydration
    void refresh()
  }, [refresh])

  const act = useCallback(async function runStateOperation(operation: () => Promise<CasinoState>, notice?: string) {
    setBusy(true)
    setError(null)
    try {
      const next = await operation()
      setState(next)
      if (notice) setLastRound(notice)
      retryOperation.current = null
      return true
    } catch (caught) {
      const reconciled = reconciledConflictState(caught)
      if (reconciled) {
        setState(reconciled)
        retryOperation.current = null
        setError('Состояние обновлено. Проверь стол и повтори действие при необходимости.')
        return false
      }
      if (!isPendingMutationBlock(caught)) {
        retryOperation.current = async () => { await runStateOperation(operation, notice) }
      } else retryOperation.current = null
      setError(caught instanceof Error ? caught.message : 'Не удалось выполнить действие')
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
      return response.result
    } catch (caught) {
      const reconciled = reconciledConflictState(caught)
      if (reconciled) {
        setState(reconciled)
        retryOperation.current = null
        setError('Состояние обновлено. Проверь стол и повтори действие при необходимости.')
        return null
      }
      if (!isPendingMutationBlock(caught)) {
        retryOperation.current = async () => {
          await runGame(game, bet, choice, expectedServerSeedHash)
        }
      } else retryOperation.current = null
      setError(caught instanceof Error ? caught.message : 'Раунд не запустился')
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
      return true
    } catch (caught) {
      const reconciled = reconciledConflictState(caught)
      if (reconciled) {
        setState(reconciled)
        retryOperation.current = null
        setError('Состояние обновлено. Проверь баланс и повтори действие при необходимости.')
        return false
      }
      if (!isPendingMutationBlock(caught)) {
        retryOperation.current = async () => { await runRefill() }
      } else retryOperation.current = null
      setError(caught instanceof Error ? caught.message : 'Не удалось пополнить баланс')
      return false
    } finally {
      setBusy(false)
    }
  }, [])

  const retry = useCallback(async () => {
    const operation = retryOperation.current
    if (operation) await operation()
    else {
      try {
        await retryPendingMutation()
        setError(null)
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Не удалось повторить запрос')
      } finally {
        await refresh()
      }
    }
  }, [refresh])

  return {
    state,
    busy,
    error,
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
