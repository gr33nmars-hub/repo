import type { CasinoState, RoundResult } from '../../types'
import { BetControl } from '../shared/BetControl'
import { PlayingCard } from './PlayingCard'
import './blackjack.css'

interface BlackjackPageProps {
  state: CasinoState
  amount: number
  minimum: number
  maximum?: number
  busy: boolean
  onAmountChange: (value: string) => void
  onStart: () => void
  onAction: (action: 'hit' | 'stand' | 'double') => void
}

const statusNames = { playing: 'Твой ход', won: 'Победа', lost: 'Раунд проигран', push: 'Ничья' } as const

export function BlackjackPage({ state, amount, minimum, maximum, busy, onAmountChange, onStart, onAction }: BlackjackPageProps) {
  const hand = state.blackjack
  const active = hand?.status === 'playing'
  const latestHandResult: RoundResult | undefined = hand && !active
    ? state.history.find((round) => round.game_id === 'blackjack')
    : undefined
  return (
    <div className="blackjack-page">
      <header className="game-page-heading">
        <div><h1>Блэкджек</h1><p>Карты и доступные действия обновляются по ответу игрового сервера.</p></div>
        {hand && <span className={`blackjack-status is-${hand.status}`}>{statusNames[hand.status]}</span>}
      </header>

      <section className="blackjack-table" aria-label="Стол блэкджека">
        <div className="blackjack-table-rim" aria-hidden="true" />
        <div className="blackjack-table-name">NOIR <span>·</span> БЛЭКДЖЕК</div>

        <div className="blackjack-hand blackjack-hand--dealer" aria-label="Карты дилера">
          <div className="blackjack-hand-heading"><span>Дилер</span><strong>{hand ? hand.dealer_score ?? 'Скрыто' : '—'}</strong></div>
          <div className="blackjack-card-row" aria-live="polite">
            {hand ? hand.dealer_cards.map((card, index) => <PlayingCard key={`dealer-${index}-${card}`} card={card} animate order={index} />) : <span className="blackjack-no-cards">Раздача ещё не началась</span>}
          </div>
        </div>

        <div className="blackjack-table-rule"><span>Решение за игроком</span><span className="blackjack-table-rule-mark" aria-hidden="true" /></div>

        <div className="blackjack-hand blackjack-hand--player" aria-label="Карты игрока">
          <div className="blackjack-hand-heading"><span>Твоя рука</span><strong>{hand?.player_score ?? '—'}</strong></div>
          <div className="blackjack-card-row" aria-live="polite">
            {hand ? hand.player_cards.map((card, index) => <PlayingCard key={`player-${index}-${card}`} card={card} animate order={index} />) : <span className="blackjack-no-cards">Ставка начнёт новую раздачу</span>}
          </div>
        </div>

        {hand && !active && (
          <div className="blackjack-round-result" role="status">
            <div><strong>{hand.message}</strong><span>{latestHandResult ? `Выплата ${latestHandResult.payout.toLocaleString('ru-RU')} · итог ${latestHandResult.profit > 0 ? '+' : ''}${latestHandResult.profit.toLocaleString('ru-RU')} фишек` : 'Раздача завершена'}</span></div>
          </div>
        )}
      </section>

      <section className="blackjack-controls" aria-label="Управление раздачей">
        <div className="blackjack-turn-copy">
          <h2>{active ? 'Твой ход' : hand ? 'Раздача завершена' : 'Начни раздачу'}</h2>
          <p>{active ? 'Выбери доступное действие. Сервер подтвердит ход и обновит карты.' : hand ? 'Сервер сохранил состояние этой раздачи.' : 'Размер ставки проверяется по лимитам стола и текущему балансу.'}</p>
        </div>
        {active ? (
          <div className="blackjack-actions" role="group" aria-label="Действия блэкджека">
            <button className="game-action-secondary" type="button" disabled={busy} onClick={() => onAction('hit')}>Взять карту</button>
            <button className="game-action-secondary" type="button" disabled={busy} onClick={() => onAction('stand')}>Остановиться</button>
            {hand.can_double && <button className="game-action-secondary is-emphasis" type="button" disabled={busy || state.player.balance < hand.bet} onClick={() => onAction('double')}>Удвоить</button>}
          </div>
        ) : (
          <BetControl amount={amount} balance={state.player.balance} minimum={minimum} maximum={maximum} evenOnly busy={busy} actionLabel={hand ? 'Новая раздача' : 'Раздать карты'} onAmountChange={onAmountChange} onSubmit={onStart} />
        )}
      </section>
    </div>
  )
}
