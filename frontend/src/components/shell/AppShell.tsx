import type { ReactNode } from 'react'
import type { PlayerState } from '../../types'
import { Icon } from './Icon'
import { NoirSidebar } from './NoirSidebar'
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
  onRetry: () => void
  onRefill: () => void
  children: ReactNode
}

export function AppShell({ room, player, balanceHeld = false, isConnected, isBusy, canRefill, error, retryAvailable, onNavigate, onRetry, onRefill, children }: AppShellProps) {
  return (
    <div className="noir-shell">
      <a className="skip-link" href="#main-content">К содержимому</a>
      <NoirSidebar
        room={room}
        player={player}
        balanceHeld={balanceHeld}
        isBusy={isBusy}
        canRefill={canRefill}
        onNavigate={onNavigate}
        onRefill={onRefill}
      />

      <div className="noir-main">
        <main className="noir-content" id="main-content" tabIndex={-1}>
          {error && error !== 'Сначала закончи текущую раздачу блэкджека' && isConnected && (
            <div className="noir-error-banner" role="alert">
              <span className="noir-error-mark" aria-hidden="true">!</span>
              <div><strong>Действие не выполнено</strong><p>{error}</p></div>
              <button type="button" onClick={onRetry}>
                <Icon name="retry" />
                {retryAvailable ? 'Повторить действие' : 'Обновить состояние'}
              </button>
            </div>
          )}
          <div className="noir-room-view" key={room}>{children}</div>
        </main>
      </div>
    </div>
  )
}
