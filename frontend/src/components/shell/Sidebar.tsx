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
  onRoomIntent: (room: RoomRoute) => void
  onRefill: () => void
}

export function Sidebar({ room, player, balanceHeld, isBusy, canRefill, onNavigate, onRoomIntent, onRefill }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Навигация NOIR Casino Club">
      <button className="sidebar__brand" onClick={() => onNavigate('lobby')} aria-label="Лобби NOIR Casino Club">
        <span className="sidebar__wordmark" aria-hidden="true"><span>N</span><span className="sidebar__wordmark-o">O</span><span>IR</span></span>
      </button>

      <nav className="sidebar__navigation" aria-label="Игровые комнаты">
        <span className="sidebar__nav-heading">КОМНАТЫ</span>
        {tableRoutes.map((route) => (
          <button
            className={`sidebar__nav-item${room === route.id ? ' sidebar__nav-item--current' : ''}`}
            key={route.id}
            type="button"
            aria-current={room === route.id ? 'page' : undefined}
            onClick={() => onNavigate(route.id)}
            onPointerEnter={() => onRoomIntent(route.id)}
            onFocus={() => onRoomIntent(route.id)}
          >
            {route.game
              ? <GameMark className="sidebar__nav-icon sidebar__nav-game-mark" game={route.game} />
              : <Icon className="sidebar__nav-icon" name={route.icon ?? 'home'} />}
            <span>{route.label}</span>
            {room === route.id && <span className="sidebar__nav-active-mark" aria-hidden="true" />}
          </button>
        ))}

        <button
          className={`sidebar__nav-item${room === 'history' ? ' sidebar__nav-item--current' : ''}`}
          type="button"
          aria-current={room === 'history' ? 'page' : undefined}
          onClick={() => onNavigate('history')}
          onPointerEnter={() => onRoomIntent('history')}
          onFocus={() => onRoomIntent('history')}
        >
          <Icon className="sidebar__nav-icon" name="history" />
          <span>История</span>
          {room === 'history' && <span className="sidebar__nav-active-mark" aria-hidden="true" />}
        </button>
      </nav>

      <div className="sidebar__footer">
        {player ? (
          <div className={`sidebar__wallet${balanceHeld ? ' sidebar__wallet--held' : ''}`} role="status" aria-label={`Баланс: ${player.balance.toLocaleString('ru-RU')} фишек${balanceHeld ? ', обновится после остановки барабанов' : ''}`}>
            <Icon name="coin" />
            <span className="sidebar__wallet-copy">
              <small>{balanceHeld ? 'БАЛАНС · ОЖИДАЕТ ОСТАНОВКИ' : 'БАЛАНС'}</small>
              <span className="sidebar__wallet-value"><strong key={player.balance}>{player.balance.toLocaleString('ru-RU')}</strong><span className="sidebar__wallet-unit">ФИШЕК</span></span>
            </span>
          </div>
        ) : (
          <div className="sidebar__wallet sidebar__wallet--loading" role="status" aria-label="Баланс загружается"><span /><span /></div>
        )}
        {canRefill && <button className="sidebar__refill" type="button" disabled={isBusy} onClick={onRefill}>{isBusy ? 'Пополняем…' : 'Пополнить баланс'}</button>}
      </div>
    </aside>
  )
}
