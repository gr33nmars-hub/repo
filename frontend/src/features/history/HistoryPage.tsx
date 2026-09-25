import type { CasinoState } from '../../types'
import { Icon } from '../../components/shell/Icon'
import './history.css'

interface HistoryPageProps {
  state: CasinoState | null
  loading: boolean
  error: string | null
  onRetry: () => void
  onOpenLobby: () => void
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function formatAmount(value: number) {
  return `${value > 0 ? '+' : ''}${value.toLocaleString('ru-RU')}`
}

export function HistoryPage({ state, loading, error, onRetry, onOpenLobby }: HistoryPageProps) {
  if (loading) {
    return <section className="history-state history-state--loading" aria-live="polite" aria-busy="true">
      <h1>Загружаем историю</h1>
      <p>Получаем завершённые раунды с локального сервера.</p>
      <div className="history-loading-lines" aria-hidden="true"><span /><span /><span /></div>
    </section>
  }

  if (error && !state) {
    return <section className="history-state history-state--error" aria-live="polite">
      <h1>История недоступна</h1>
      <p>{error}</p>
      <button className="game-action-secondary" type="button" onClick={onRetry}><Icon name="retry" />Повторить запрос</button>
    </section>
  }

  const rounds = state?.history ?? []

  return (
    <div className="history-page">
      <header className="game-page-heading">
        <div><h1>История раундов</h1><p>Последние завершённые игры, полученные от локального сервера.</p></div>
        <span className="history-count">{rounds.length}</span>
      </header>

      {rounds.length ? (
        <ol className="history-round-list" aria-label="Последние раунды">
          {rounds.map((round, index) => (
            <li className="history-round" key={`${round.played_at}-${round.game_id}-${index}`}>
              <div className="history-round-main">
                <strong>{round.game_name}</strong>
                <span>{round.message}</span>
                <time dateTime={round.played_at}>{formatDate(round.played_at)}</time>
              </div>
              <dl className="history-round-amounts">
                <div><dt>Ставка</dt><dd>{round.bet.toLocaleString('ru-RU')}</dd></div>
                <div><dt>Выплата</dt><dd>{round.payout.toLocaleString('ru-RU')}</dd></div>
                <div className={round.profit > 0 ? 'is-positive' : round.profit < 0 ? 'is-negative' : ''}>
                  <dt>Итог</dt><dd>{formatAmount(round.profit)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ol>
      ) : (
        <section className="history-state history-state--empty" aria-live="polite">
          <h2>Завершённых раундов пока нет</h2>
          <p>После первой завершённой игры сервер добавит её сюда.</p>
          <button className="game-action-secondary" type="button" onClick={onOpenLobby}>Перейти в лобби <Icon name="arrow" /></button>
        </section>
      )}
    </div>
  )
}
