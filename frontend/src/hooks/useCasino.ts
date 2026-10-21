import { useCallback, useEffect, useState } from 'react'
import { casinoApi } from '../lib/casino.api'
import type { BlackjackAction, CasinoState, GameId, RouletteChoice } from '../types'

export function useCasino() {
  const [state, setState] = useState<CasinoState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await casinoApi.state()
      setState(data)
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось связаться с сервером казино')
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const play = useCallback(async (
    game: Exclude<GameId, 'blackjack'>,
    bet: number,
    choice = '',
  ) => {
    setBusy(true)
    setError(null)
    try {
      const response = await casinoApi.play(game, bet, choice)
      setState(response.state)
      return response.result
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Ошибка во время проведения раунда')
      return null
    } finally {
      setBusy(false)
    }
  }, [])

  const startBlackjack = useCallback(async (bet: number) => {
    setBusy(true)
    setError(null)
    try {
      const nextState = await casinoApi.startBlackjack(bet)
      setState(nextState)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось начать раздачу карт')
    } finally {
      setBusy(false)
    }
  }, [])

  const blackjackAction = useCallback(async (action: BlackjackAction) => {
    setBusy(true)
    setError(null)
    try {
      const nextState = await casinoApi.blackjackAction(action)
      setState(nextState)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось выполнить игровое действие')
    } finally {
      setBusy(false)
    }
  }, [])

  const rotateSeed = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const response = await casinoApi.rotateSeed()
      setState(response.state)
      return response
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось сменить сид')
      return null
    } finally {
      setBusy(false)
    }
  }, [])

  const refill = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await casinoApi.refill()
      setState(res.state)
      return true
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось пополнить баланс')
      return false
    } finally {
      setBusy(false)
    }
  }, [])

  return {
    state,
    busy,
    error,
    refresh,
    play,
    startBlackjack,
    blackjackAction,
    rotateSeed,
    refill,
    clearError: () => setError(null),
  }
}

export type { RouletteChoice }
