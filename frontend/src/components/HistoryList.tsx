import type { RoundResult } from '../types'

interface HistoryListProps {
  rounds: RoundResult[]
  compact?: boolean
}

const icons = { slots: '✳', roulette: '◉', blackjack: '♠' }

export function HistoryList({ rounds, compact = false }: HistoryListProps) {
  const visible = compact ? rounds.slice(0, 4) : rounds
  if (!visible.length) {
    return <div className="history-empty"><span className="history-empty-icon">↗</span><p>Первый раунд ждёт тебя за столом.</p></div>
  }
  return <div className="history-list">
    {visible.map((round, index) => (
      <article className="history-row" key={`${round.played_at}-${index}`}>
        <div className={`history-game-icon history-game-icon--${round.game_id}`}>{icons[round.game_id]}</div>
        <div className="history-copy">
          <strong>{round.game_name}</strong>
          <span>{round.message}</span>
        </div>
        <div className="history-result">
          <strong className={round.profit > 0 ? 'positive' : round.profit < 0 ? 'negative' : ''}>
            {round.profit > 0 ? '+' : ''}{round.profit.toLocaleString('ru-RU')} <i>◉</i>
          </strong>
          <span>ставка {round.bet.toLocaleString('ru-RU')}</span>
        </div>
      </article>
    ))}
  </div>
}
