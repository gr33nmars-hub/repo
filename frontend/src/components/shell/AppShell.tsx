import type { ReactNode } from 'react'
import type { PlayerState } from '../../types'
import { Icon } from './Icon'
import { Sidebar } from './Sidebar'
import type { RoomRoute } from './RoomRoute'

export type { RoomRoute } from './RoomRoute'

interface AppShellProps {
  room: RoomRoute
  player: PlayerState | null
  balanceHeld?: boolean
  isConnected: boolean
  isBusy: boolean
  canRefill: boolean
  error: string | null
  retryAvailable: boolean
  onNavigate: (room: RoomRoute) => void
  onRoomIntent: (room: RoomRoute) => void
  onRetry: () => void
  onRefill: () => void
  children: ReactNode
}

export function AppShell({ room, player, balanceHeld = false, isConnected, isBusy, canRefill, error, retryAvailable, onNavigate, onRoomIntent, onRetry, onRefill, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">К содержимому</a>
      <Sidebar
        room={room}
        player={player}
        balanceHeld={balanceHeld}
        isBusy={isBusy}
        canRefill={canRefill}
        onNavigate={onNavigate}
        onRoomIntent={onRoomIntent}
        onRefill={onRefill}
      />

      <div className="app-shell__main">
        <main className="app-shell__content" id="main-content" tabIndex={-1}>
          {error && error !== 'Сначала закончи текущую раздачу блэкджека' && isConnected && (
            <div className="app-shell__error-banner" role="alert">
              <span className="app-shell__error-mark" aria-hidden="true">!</span>
              <div><strong>Действие не выполнено</strong><p>{error}</p></div>
              <button type="button" disabled={isBusy} onClick={onRetry}>
                <Icon name="retry" />
                {retryAvailable ? 'Повторить действие' : 'Обновить состояние'}
              </button>
            </div>
          )}
          <div className="app-shell__room-view" key={room}>{children}</div>
        </main>
      </div>
    </div>
  )
}
