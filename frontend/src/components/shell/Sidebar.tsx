import { Icon, type ShellIconName } from './Icon'
import { GameMark } from './GameMark'
import type { GameId, PlayerState } from '../../types'
import type { RoomRoute } from './RoomRoute'

const tableRoutes: { id: Exclude<RoomRoute, 'history'>; label: string; icon?: ShellIconName; game?: GameId }[] = [
  { id: 'lobby', label: 'Лобби', icon: 'home' },
  { id: 'blackjack', label: 'Блэкджек', game: 'blackjack' },
  { id: 'slots', label: 'Слоты', game: 'slots' },
  { id: 'roulette', label: 'Рулетка', game: 'roulette' },
]

interface SidebarProps {
  room: RoomRoute
  player: PlayerState | null
  balanceHeld: boolean
  isBusy: boolean
  canRefill: boolean
  onNavigate: (room: RoomRoute) => void
  onRefill: () => void
}

export function Sidebar({ room, player, balanceHeld, isBusy, canRefill, onNavigate, onRefill }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Навигация NOIR Casino Club">
      <button className="sidebar-brand" onClick={() => onNavigate('lobby')} aria-label="Лобби NOIR Casino Club">
        <span className="sidebar-wordmark" aria-hidden="true"><span>N</span><span className="sidebar-wordmark-o">O</span><span>IR</span></span>
      </button>

      <nav className="sidebar-navigation" aria-label="Игровые комнаты">
        <span className="sidebar-nav-heading">КОМНАТЫ</span>
        {tableRoutes.map((route) => (
          <button
            className={`sidebar-nav-item${room === route.id ? ' is-current' : ''}`}
            key={route.id}
            type="button"
            aria-current={room === route.id ? 'page' : undefined}
            onClick={() => onNavigate(route.id)}
          >
            {route.game
              ? <GameMark className="sidebar-nav-icon sidebar-nav-game-mark" game={route.game} />
              : <Icon className="sidebar-nav-icon" name={route.icon ?? 'home'} />}
            <span>{route.label}</span>
            {room === route.id && <span className="sidebar-nav-active-mark" aria-hidden="true" />}
          </button>
        ))}

        <span className="sidebar-nav-heading sidebar-nav-heading--secondary">ЗАПИСИ</span>
        <button
          className={`sidebar-nav-item${room === 'history' ? ' is-current' : ''}`}
          type="button"
          aria-current={room === 'history' ? 'page' : undefined}
          onClick={() => onNavigate('history')}
        >
          <Icon className="sidebar-nav-icon" name="history" />
          <span>История</span>
          {room === 'history' && <span className="sidebar-nav-active-mark" aria-hidden="true" />}
        </button>
      </nav>

      <div className="sidebar-footer">
        {player ? (
          <div className={`sidebar-wallet${balanceHeld ? ' is-held' : ''}`} role="status" aria-label={`Баланс: ${player.balance.toLocaleString('ru-RU')} фишек${balanceHeld ? ', обновится после остановки барабанов' : ''}`}>
            <Icon name="coin" />
            <span className="sidebar-wallet-copy">
              <small>{balanceHeld ? 'БАЛАНС · ОЖИДАЕТ ОСТАНОВКИ' : 'БАЛАНС'}</small>
              <span className="sidebar-wallet-value"><strong key={player.balance}>{player.balance.toLocaleString('ru-RU')}</strong><span className="sidebar-wallet-unit">ФИШЕК</span></span>
            </span>
          </div>
        ) : (
          <div className="sidebar-wallet sidebar-wallet--loading" role="status" aria-label="Баланс загружается"><span /><span /></div>
        )}
        {canRefill && <button className="sidebar-refill" type="button" disabled={isBusy} onClick={onRefill}>{isBusy ? 'Пополняем…' : 'Пополнить баланс'}</button>}
      </div>
    </aside>
  )
}
