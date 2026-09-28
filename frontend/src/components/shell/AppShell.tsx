import type { ReactNode } from 'react'
import type { GameId, PlayerState } from '../../types'
import { Icon, type ShellIconName } from './Icon'
import { GameMark } from './GameMark'

export type RoomRoute = 'lobby' | 'blackjack' | 'slots' | 'roulette' | 'history'

const tableRoutes: { id: RoomRoute; label: string; icon?: ShellIconName; game?: GameId }[] = [
  { id: 'lobby', label: 'Лобби', icon: 'home' },
  { id: 'blackjack', label: 'Блэкджек', game: 'blackjack' },
  { id: 'slots', label: 'Слоты', game: 'slots' },
  { id: 'roulette', label: 'Рулетка', game: 'roulette' },
]

const roomNames: Record<RoomRoute, string> = {
  lobby: 'Лобби',
  blackjack: 'Блэкджек',
  slots: 'Слоты',
  roulette: 'Рулетка',
  history: 'История',
}

interface AppShellProps {
  room: RoomRoute
  player: PlayerState | null
  isConnected: boolean
  isBusy: boolean
  canRefill: boolean
  error: string | null
  retryAvailable: boolean
  notice: string | null
  onNavigate: (room: RoomRoute) => void
  onRetry: () => void
  onRefill: () => void
  children: ReactNode
}

export function AppShell({ room, player, isConnected, isBusy, canRefill, error, retryAvailable, notice, onNavigate, onRetry, onRefill, children }: AppShellProps) {
  return (
    <div className="noir-shell">
      <a className="skip-link" href="#main-content">К содержимому</a>
      <aside className="noir-sidebar" aria-label="Навигация NOIR Casino">
        <button className="noir-brand" onClick={() => onNavigate('lobby')} aria-label="Лобби">
          <span className="noir-brand-mark" aria-hidden="true">N<Icon name="blackjack" /></span>
          <span className="noir-brand-copy"><strong>NOIR</strong><small>CASINO CLUB</small></span>
        </button>

        <nav className="noir-navigation" aria-label="Разделы казино">
          <span className="noir-nav-heading">СТОЛЫ</span>
          {tableRoutes.map((route) => (
            <button
              className={`noir-nav-item${room === route.id ? ' is-current' : ''}`}
              key={route.id}
              type="button"
              aria-label={route.label}
              aria-current={room === route.id ? 'page' : undefined}
              onClick={() => onNavigate(route.id)}
            >
              {route.game
                ? <GameMark className="noir-nav-icon noir-nav-game-mark" game={route.game} />
                : <Icon className="noir-nav-icon" name={route.icon ?? 'home'} />}
              <span>{route.label}</span>
              {room === route.id && <span className="noir-nav-active-mark" aria-hidden="true" />}
            </button>
          ))}

          <span className="noir-nav-heading noir-nav-heading--secondary">ТВОЯ ИГРА</span>
          <button
            className={`noir-nav-item${room === 'history' ? ' is-current' : ''}`}
            type="button"
            aria-label="История"
            aria-current={room === 'history' ? 'page' : undefined}
            onClick={() => onNavigate('history')}
          >
            <Icon className="noir-nav-icon" name="history" />
            <span>История</span>
            {room === 'history' && <span className="noir-nav-active-mark" aria-hidden="true" />}
          </button>
        </nav>

      </aside>

      <div className="noir-main">
        <header className="noir-topbar">
          <div className="noir-breadcrumb" aria-label="Текущий раздел">
            <span>NOIR</span><span className="noir-breadcrumb-separator" aria-hidden="true">/</span><strong>{roomNames[room]}</strong>
          </div>
          <div className="noir-topbar-actions">
            <span className={`noir-api-indicator${isConnected ? ' is-ready' : error ? ' is-error' : ''}`}>
              <Icon name="wifi" />
              <span>{isConnected ? error ? 'Ошибка запроса' : 'На связи' : error ? 'Нет связи' : 'Подключение'}</span>
            </span>
            {player ? (
              <div className="noir-wallet" aria-label={`Баланс: ${player.balance.toLocaleString('ru-RU')} фишек`}>
                <Icon name="coin" />
                <span className="noir-wallet-copy"><small>БАЛАНС</small><strong key={player.balance}>{player.balance.toLocaleString('ru-RU')}</strong></span>
                <span className="noir-wallet-unit">ФИШЕК</span>
              </div>
            ) : (
              <div className="noir-wallet noir-wallet--loading" aria-label="Баланс загружается"><span /><span /></div>
            )}
            {canRefill && <button className="noir-refill" type="button" disabled={isBusy} onClick={onRefill}>{isBusy ? 'Пополняем…' : 'Пополнить баланс'}</button>}
          </div>
        </header>

        <main className="noir-content" id="main-content" tabIndex={-1}>
          {error && isConnected && (
            <div className="noir-error-banner" role="alert">
              <span className="noir-error-mark" aria-hidden="true">!</span>
              <div><strong>Действие не выполнено</strong><p>{error}</p></div>
              <button type="button" onClick={onRetry}>
                <Icon name="retry" />{retryAvailable ? 'Повторить действие' : 'Обновить состояние'}
              </button>
            </div>
          )}
          {notice && !error && <div className="noir-notice" role="status">{notice}</div>}
          <div className="noir-room-view" key={room}>{children}</div>
        </main>
      </div>
    </div>
  )
}
