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
    return (
      <section className="history-state history-state--loading" aria-live="polite" aria-busy="true">
        <h1>Журнал раундов</h1>
        <div className="history-loading-lines" aria-hidden="true"><span /><span /><span /></div>
      </section>
    )
  }

  if (error && !state) {
    return (
      <section className="history-state history-state--error" aria-live="polite">
        <h1>История временно недоступна</h1>
        <p>{error}</p>
        <button className="game-action-secondary" type="button" onClick={onRetry}>
          <Icon name="retry" />
          Повторить запрос
        </button>
      </section>
    )
  }

  const rounds = state?.history ?? []

  return (
    <div className="history-page">
      <header className="game-page-heading">
        <div>
          <h1>Журнал раундов</h1>
          <p>Аудит ставок, исходов и криптографических доказательств Provably Fair (HMAC-SHA256).</p>
        </div>
        <span className="history-count">Последние {rounds.length}</span>
      </header>

      {rounds.length ? (
        <ol className="history-round-list" aria-label="Последние раунды">
          {rounds.map((round, index) => (
            <li className="history-round" key={`${round.played_at}-${round.game_id}-${index}`}>
              <div className="history-round-main">
                <strong>{round.game_name}</strong>
                <span>{round.message}</span>
                <time dateTime={round.played_at}>{formatDate(round.played_at)}</time>
                {round.fairness && (
                  <div style={{ marginTop: '6px', fontSize: '10px', color: '#8d9489', fontFamily: 'var(--mono)' }}>
                    SHA-256 Hash: {round.fairness.server_seed_hash ? `${round.fairness.server_seed_hash.slice(0, 16)}...` : 'N/A'} (Nonce: {round.fairness.nonce})
                  </div>
                )}
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
          <h2>Завершенных раундов пока нет</h2>
          <p>Сыгранные партии отобразятся в этом реестре с хешем раунда.</p>
          <button className="game-action-secondary" type="button" onClick={onOpenLobby}>
            Перейти к столам <Icon name="arrow" />
          </button>
        </section>
      )}
    </div>
  )
}
