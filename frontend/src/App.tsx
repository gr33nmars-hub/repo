import { Component, lazy, startTransition, Suspense, useState, type ReactNode } from 'react'
import { AppShell, type RoomRoute } from './components/shell/AppShell'
import { LobbyPage } from './components/lobby/LobbyPage'
import { useCasino } from './hooks/useCasino'
import type { RouletteChoice } from './types'
import './styles/shell.css'
import './features/shared/game-ui.css'

const roomModules = {
  blackjack: () => import('./features/blackjack/BlackjackPage'),
  roulette: () => import('./features/roulette/RoulettePage'),
  slots: () => import('./features/slots/SlotsPage'),
  history: () => import('./features/history/HistoryPage'),
}
const BlackjackPage = lazy(() => roomModules.blackjack().then((module) => ({ default: module.BlackjackPage })))
const RoulettePage = lazy(() => roomModules.roulette().then((module) => ({ default: module.RoulettePage })))
const SlotsPage = lazy(() => roomModules.slots().then((module) => ({ default: module.SlotsPage })))
const HistoryPage = lazy(() => roomModules.history().then((module) => ({ default: module.HistoryPage })))

function preloadRoom(room: RoomRoute) {
  if (room !== 'lobby') void roomModules[room]().catch(() => {
    // Opening the screen reports a load failure through RoomErrorBoundary.
  })
}

class RoomErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (this.state.failed) return <section className="game-unavailable" role="alert">
      <h1>Не удалось открыть экран</h1>
      <p>Перезапусти приложение и попробуй снова.</p>
      <button className="game-action--secondary" type="button" onClick={() => window.location.reload()}>Перезапустить</button>
    </section>
    return this.props.children
  }
}

function App() {
  const casino = useCasino()
  const [room, setRoom] = useState<RoomRoute>('lobby')
  const [bet, setBet] = useState<number | null>(null)
  const [rouletteChoice, setRouletteChoice] = useState<RouletteChoice>('red')
  const [slotHeldBalance, setSlotHeldBalance] = useState<number | null>(null)
  const state = casino.state
  const blackjackInProgress = state?.blackjack?.status === 'playing' || state?.blackjack?.status === 'insurance'
  const balance = state?.player.balance ?? 0
  const shownBalance = room === 'slots' && slotHeldBalance !== null ? slotHeldBalance : balance
  const gameInfo = room === 'blackjack' || room === 'slots' || room === 'roulette'
    ? state?.games.find((game) => game.id === room)
    : undefined
  const minimumBet = gameInfo?.minimum_bet ?? 0
  const amount = bet ?? minimumBet
  const refillMinimum = state?.games.find((game) => game.id === 'blackjack')?.minimum_bet ?? 0

  function setWager(value: string) {
    setBet(value.trim() ? Number(value) : 0)
  }

  function navigate(next: RoomRoute) {
    startTransition(() => setRoom(next))
  }

  const unavailablePage = (
    <section className="game-unavailable" role="status">
      <h1>Не удалось загрузить стол</h1>
      <p>Обнови игру и попробуй снова.</p>
      <button className="game-action--secondary" type="button" onClick={() => void casino.refresh()}>
        Повторить
      </button>
    </section>
  )
  let gamePage: ReactNode = null
  switch (room) {
    case 'history':
      gamePage = (
        <HistoryPage
          state={state}
          loading={!state && !casino.error}
          error={!state ? casino.error : null}
          onRetry={() => void casino.refresh()}
          onOpenLobby={() => navigate('lobby')}
        />
      )
      break
    case 'lobby':
      if (state) {
        gamePage = <LobbyPage state={state} onOpen={navigate} onRetry={() => void casino.refresh()} />
      }
      break
    case 'blackjack':
      if (!state) break
      if (!gameInfo) {
        gamePage = unavailablePage
        break
      }
      gamePage = (
        <BlackjackPage
          state={state}
          amount={amount}
          minimum={gameInfo.minimum_bet}
          maximum={gameInfo.maximum_bet}
          busy={casino.busy}
          onAmountChange={setWager}
          onStart={() => void casino.startBlackjack(amount, state.server_seed_hash ?? undefined)}
          onAction={(action) => void casino.blackjackAction(action)}
        />
      )
      break
    case 'slots':
      if (!state) break
      if (!gameInfo) {
        gamePage = unavailablePage
        break
      }
      gamePage = (
        <SlotsPage
          game={gameInfo}
          balance={shownBalance}
          amount={amount}
          busy={casino.busy}
          blocked={blackjackInProgress}
          initialRound={state.history.find((round) => round.game_id === 'slots')}
          onBalanceHold={setSlotHeldBalance}
          onAmountChange={setWager}
          onPlay={() => casino.play('slots', amount, '', state.slots_server_seed_hash ?? undefined)}
        />
      )
      break
    case 'roulette':
      if (!state) break
      if (!gameInfo) {
        gamePage = unavailablePage
        break
      }
      gamePage = (
        <RoulettePage
          game={gameInfo}
          balance={balance}
          amount={amount}
          choice={rouletteChoice}
          busy={casino.busy}
          blocked={blackjackInProgress}
          onAmountChange={setWager}
          onChoice={setRouletteChoice}
          initialRound={state.history.find((round) => round.game_id === 'roulette')}
          onPlay={() => casino.play('roulette', amount, rouletteChoice, state.server_seed_hash ?? undefined)}
        />
      )
      break
  }

  return (
    <AppShell room={room} player={state ? { ...state.player, balance: shownBalance } : null} balanceHeld={room === 'slots' && slotHeldBalance !== null} isConnected={Boolean(state)} isBusy={casino.busy || slotHeldBalance !== null} canRefill={Boolean(state && slotHeldBalance === null && refillMinimum > 0 && state.player.balance < refillMinimum)} error={room === 'history' && !state ? null : casino.error} retryAvailable={casino.retryAvailable} onNavigate={navigate} onRoomIntent={preloadRoom} onRetry={() => void casino.retry()} onRefill={() => void casino.refill()}>
      <Suspense fallback={<section className="app-loading" role="status" aria-busy="true"><strong>Загружаем экран…</strong></section>}>
        <RoomErrorBoundary key={room}>
          {gamePage ?? (casino.error ? (
            <section className="lobby-page__empty lobby-page__empty--connection" aria-live="polite">
              <h1>Нет связи с игрой</h1>
              <p>Проверь подключение и попробуй снова.</p>
              <button type="button" onClick={() => void casino.refresh()}>Подключиться снова</button>
            </section>
          ) : (
            <section className="app-loading" aria-live="polite" aria-busy="true">
              <span className="app-loading__mark" aria-hidden="true">N</span>
              <strong>Запускаем игру</strong>
              <span>Подключаемся к серверу…</span>
            </section>
          ))}
        </RoomErrorBoundary>
      </Suspense>
    </AppShell>
  )
}

export default App
