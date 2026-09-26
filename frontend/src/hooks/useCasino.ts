import { useCallback, useEffect, useState } from 'react'
import { casinoApi } from '../lib/casino.api'
import type { BlackjackAction, CasinoState, GameId, RouletteChoice } from '../types'

export function useCasino() {
  const [state, setState] = useState<CasinoState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRound, setLastRound] = useState<string | null>(null)

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

  const act = useCallback(async (operation: () => Promise<CasinoState>, notice?: string) => {
    setBusy(true)
    setError(null)
    try {
      const next = await operation()
      setState(next)
      if (notice) setLastRound(notice)
      return true
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось выполнить действие')
      return false
    } finally {
      setBusy(false)
    }
  }, [])

  const play = useCallback(async (game: Exclude<GameId, 'blackjack'>, bet: number, choice = '') => {
    setBusy(true)
    setError(null)
    try {
      const response = await casinoApi.play(game, bet, choice)
      setState(response.state)
      setLastRound(response.result.message)
      return response.result
    } catch (caught) {
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

  const refill = useCallback(() => act(async () => {
    await casinoApi.refill()
    return casinoApi.state()
  }, 'Демо-баланс пополнен'), [act])

  return {
    state,
    busy,
    error,
    lastRound,
    refresh,
    play,
    startBlackjack,
    blackjackAction,
    refill,
    clearNotice: () => setLastRound(null),
    clearError: () => setError(null),
  }
}

export type { RouletteChoice }
