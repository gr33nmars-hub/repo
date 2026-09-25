import { useEffect, useState } from 'react'
import { AppShell, type RoomRoute } from './components/shell/AppShell'
import { LobbyPage } from './components/lobby/LobbyPage'
import { BlackjackPage } from './features/blackjack/BlackjackPage'
import { RoulettePage } from './features/roulette/RoulettePage'
import { SlotsPage } from './features/slots/SlotsPage'
import { HistoryPage } from './features/history/HistoryPage'
import { useCasino } from './hooks/useCasino'
import { stopBackend } from './lib/casino.api'
import type { RouletteChoice } from './types'
import './styles/shell.css'
import './features/shared/game-ui.css'

function App() {
  const casino = useCasino()
  const [room, setRoom] = useState<RoomRoute>('lobby')
  const [bet, setBet] = useState<number | null>(null)
  const [rouletteChoice, setRouletteChoice] = useState<RouletteChoice>('red')
  const state = casino.state
  const balance = state?.player.balance ?? 0
  const gameInfo = room === 'blackjack' || room === 'slots' || room === 'roulette'
    ? state?.games.find((game) => game.id === room)
    : undefined
  const minimumBet = gameInfo?.minimum_bet ?? 0
  const amount = bet ?? minimumBet
  const refillMinimum = state?.games.find((game) => game.id === 'blackjack')?.minimum_bet ?? 0

  useEffect(() => {
    window.addEventListener('beforeunload', stopBackend)
    return () => window.removeEventListener('beforeunload', stopBackend)
  }, [])

  function setWager(value: string) {
    setBet(value.trim() ? Number(value) : 0)
  }

  const gamePage = room === 'history'
    ? <HistoryPage state={state} loading={!state && !casino.error} error={!state ? casino.error : null} onRetry={() => void casino.refresh()} onOpenLobby={() => setRoom('lobby')} />
    : state && room === 'lobby'
      ? <LobbyPage state={state} onOpen={setRoom} onRetry={() => void casino.refresh()} />
      : state && room === 'blackjack' && gameInfo
        ? <BlackjackPage state={state} amount={amount} minimum={gameInfo.minimum_bet} maximum={gameInfo.maximum_bet} busy={casino.busy} onAmountChange={setWager} onStart={() => void casino.startBlackjack(amount)} onAction={(action) => void casino.blackjackAction(action)} />
        : state && room === 'slots' && gameInfo
          ? <SlotsPage game={gameInfo} balance={balance} amount={amount} busy={casino.busy} onAmountChange={setWager} onPlay={() => casino.play('slots', amount)} />
          : state && room === 'roulette' && gameInfo
            ? <RoulettePage game={gameInfo} balance={balance} amount={amount} choice={rouletteChoice} busy={casino.busy} onAmountChange={setWager} onChoice={setRouletteChoice} onPlay={() => casino.play('roulette', amount, rouletteChoice)} />
            : state && (room === 'blackjack' || room === 'slots' || room === 'roulette')
              ? <section className="game-unavailable" role="status"><h1>Стол недоступен</h1><p>Игровой сервер не включил этот стол в текущее состояние.</p><button className="game-action-secondary" type="button" onClick={() => void casino.refresh()}>Обновить состояние</button></section>
              : null

  return (
    <AppShell room={room} player={state?.player ?? null} isConnected={Boolean(state)} isBusy={casino.busy} canRefill={Boolean(state && refillMinimum > 0 && state.player.balance < refillMinimum)} error={room === 'history' && !state ? null : casino.error} notice={room === 'lobby' ? casino.lastRound : null} onNavigate={setRoom} onRetry={() => void casino.refresh()} onRefill={() => void casino.refill()}>
      {gamePage ?? (casino.error ? (
        <section className="lobby-empty lobby-empty--connection" aria-live="polite">
          <h1>Клуб пока закрыт</h1>
          <p>Не удалось получить состояние игрового сервера. Проверьте соединение и повторите запрос.</p>
          <button type="button" onClick={() => void casino.refresh()}>Повторить подключение</button>
        </section>
      ) : (
        <section className="noir-loading" aria-live="polite" aria-busy="true">
          <span className="noir-loading-mark" aria-hidden="true">N</span>
          <strong>Открываем клуб</strong>
          <span>Получаем баланс и столы с локального сервера</span>
        </section>
      ))}
    </AppShell>
  )
}

export default App
