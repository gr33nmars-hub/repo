import { useState, type ReactNode } from 'react'
import { AppShell, type RoomRoute } from './components/shell/AppShell'
import { LobbyPage } from './components/lobby/LobbyPage'
import { BlackjackPage } from './features/blackjack/BlackjackPage'
import { RoulettePage } from './features/roulette/RoulettePage'
import { SlotsPage } from './features/slots/SlotsPage'
import { HistoryPage } from './features/history/HistoryPage'
import { useCasino } from './hooks/useCasino'
import type { RouletteChoice } from './types'
import './styles/shell.css'
import './features/shared/game-ui.css'

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

  const unavailablePage = (
    <section className="game-unavailable" role="status">
      <h1>Стол недоступен</h1>
      <button className="game-action-secondary" type="button" onClick={() => void casino.refresh()}>
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
          onOpenLobby={() => setRoom('lobby')}
        />
      )
      break
    case 'lobby':
      if (state) {
        gamePage = <LobbyPage state={state} onOpen={setRoom} onRetry={() => void casino.refresh()} />
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
    <AppShell room={room} player={state ? { ...state.player, balance: shownBalance } : null} balanceHeld={room === 'slots' && slotHeldBalance !== null} isConnected={Boolean(state)} isBusy={casino.busy || slotHeldBalance !== null} canRefill={Boolean(state && slotHeldBalance === null && refillMinimum > 0 && state.player.balance < refillMinimum)} error={room === 'history' && !state ? null : casino.error} retryAvailable={casino.retryAvailable} onNavigate={setRoom} onRetry={() => void casino.retry()} onRefill={() => void casino.refill()}>
      {gamePage ?? (casino.error ? (
        <section className="lobby-empty lobby-empty--connection" aria-live="polite">
          <h1>Клуб пока закрыт</h1>
          <p>Проверьте соединение и попробуйте ещё раз.</p>
          <button type="button" onClick={() => void casino.refresh()}>Повторить</button>
        </section>
      ) : (
        <section className="app-loading" aria-live="polite" aria-busy="true">
          <span className="app-loading-mark" aria-hidden="true">N</span>
          <strong>Открываем клуб</strong>
          <span>Подключаемся…</span>
        </section>
      ))}
    </AppShell>
  )
}

export default App
