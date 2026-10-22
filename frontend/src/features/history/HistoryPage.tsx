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
    return <section className="history-page__state history-page__state--loading" aria-live="polite" aria-busy="true">
      <h1>Загружаем историю</h1>
      <div className="history-page__loading-lines" aria-hidden="true"><span /><span /><span /></div>
    </section>
  }

  if (error && !state) {
    return <section className="history-page__state history-page__state--error" aria-live="polite">
      <h1>История недоступна</h1>
      <p>{error}</p>
      <button className="game-action--secondary" type="button" onClick={onRetry}><Icon name="retry" />Загрузить историю снова</button>
    </section>
  }

  const rounds = state?.history ?? []

  return (
    <div className="history-page">
      <header className="game-page-heading">
        <div><h1 className="game-page-heading__title">История раундов</h1><p className="game-page-heading__description">Ставки, выплаты и итоги.</p></div>
        <span className="history-page__count">{rounds.length}</span>
      </header>

      {rounds.length ? (
        <ol className="history-page__round-list" aria-label="Последние раунды">
          {rounds.map((round, index) => (
            <li className="history-page__round" key={`${round.played_at}-${round.game_id}-${index}`}>
              <div className="history-page__round-main">
                <strong>{round.game_name}</strong>
                {round.verification_status && <small className="history-page__round-verification">
                  {round.verification_status === 'verified' ? 'Результат подтверждён'
                    : round.verification_status === 'legacy-unverified' ? 'Старая запись · результат не проверялся'
                      : 'Результат не прошёл проверку'}
                </small>}
                <span>{round.message}</span>
                <time dateTime={round.played_at}>{formatDate(round.played_at)}</time>
              </div>
              <dl className="history-page__round-amounts">
                <div><dt>Ставка</dt><dd>{round.bet.toLocaleString('ru-RU')}</dd></div>
                <div><dt>Выплата</dt><dd>{round.payout.toLocaleString('ru-RU')}</dd></div>
                <div className={`history-page__round-amount${round.profit > 0 ? ' history-page__round-amount--positive' : round.profit < 0 ? ' history-page__round-amount--negative' : ''}`}>
                  <dt>Итог</dt><dd>{formatAmount(round.profit)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ol>
      ) : (
        <section className="history-page__state history-page__state--empty" aria-live="polite">
          <h2>Завершённых раундов пока нет</h2>
          <p>Сыгранные раунды появятся здесь.</p>
          <button className="game-action--secondary" type="button" onClick={onOpenLobby}>Перейти в лобби <Icon name="arrow" /></button>
        </section>
      )}
    </div>
  )
}
