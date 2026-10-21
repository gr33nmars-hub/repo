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

interface NoirSidebarProps {
  room: RoomRoute
  player: PlayerState | null
  balanceHeld: boolean
  isBusy: boolean
  canRefill: boolean
  onNavigate: (room: RoomRoute) => void
  onRefill: () => void
}

export function NoirSidebar({ room, player, balanceHeld, isBusy, canRefill, onNavigate, onRefill }: NoirSidebarProps) {
  return (
    <aside className="noir-sidebar" aria-label="Навигация NOIR Casino">
      <button className="noir-brand" onClick={() => onNavigate('lobby')} aria-label="Лобби NOIR Casino Club">
        <span className="noir-wordmark" aria-hidden="true"><span>N</span><span className="noir-wordmark-o">O</span><span>IR</span></span>
      </button>

      <nav className="noir-navigation" aria-label="Игровые комнаты">
        <span className="noir-nav-heading">КОМНАТЫ</span>
        {tableRoutes.map((route) => (
          <button
            className={`noir-nav-item${room === route.id ? ' is-current' : ''}`}
            key={route.id}
            type="button"
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

        <span className="noir-nav-heading noir-nav-heading--secondary">ЗАПИСИ</span>
        <button
          className={`noir-nav-item${room === 'history' ? ' is-current' : ''}`}
          type="button"
          aria-current={room === 'history' ? 'page' : undefined}
          onClick={() => onNavigate('history')}
        >
          <Icon className="noir-nav-icon" name="history" />
          <span>История</span>
          {room === 'history' && <span className="noir-nav-active-mark" aria-hidden="true" />}
        </button>
      </nav>

      <div className="noir-sidebar-footer">
        {player ? (
          <div className={`noir-wallet${balanceHeld ? ' is-held' : ''}`} role="status" aria-label={`Баланс: ${player.balance.toLocaleString('ru-RU')} фишек${balanceHeld ? ', обновится после остановки барабанов' : ''}`}>
            <Icon name="coin" />
            <span className="noir-wallet-copy">
              <small>{balanceHeld ? 'БАЛАНС · ОЖИДАЕТ ОСТАНОВКИ' : 'БАЛАНС'}</small>
              <span className="noir-wallet-value"><strong key={player.balance}>{player.balance.toLocaleString('ru-RU')}</strong><span className="noir-wallet-unit">ФИШЕК</span></span>
            </span>
          </div>
        ) : (
          <div className="noir-wallet noir-wallet--loading" role="status" aria-label="Баланс загружается"><span /><span /></div>
        )}
        {canRefill && <button className="noir-refill" type="button" disabled={isBusy} onClick={onRefill}>{isBusy ? 'Пополняем…' : 'Пополнить баланс'}</button>}
      </div>
    </aside>
  )
}
