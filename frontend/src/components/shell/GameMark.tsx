import type { GameId } from '../../types'

export function GameMark({ game, className }: { game: GameId; className?: string }) {
  return (
    <svg className={`game-mark${className ? ` ${className}` : ''}`} data-game-mark={game} viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
      {game === 'blackjack' && <>
        <path d="M18 7h28a4 4 0 0 1 4 4v42H14V11a4 4 0 0 1 4-4Z" />
        <text className="game-mark__number" x="32" y="39" textAnchor="middle">21</text>
      </>}
      {game === 'roulette' && <>
        <circle cx="32" cy="32" r="24.5" />
        <circle cx="32" cy="32" r="19" />
        <circle cx="32" cy="32" r="6.5" />
        <path d="M32 7.5v5m0 39v5m24.5-24.5h-5m-39 0h-5M49.3 14.7l-3.6 3.6m-27.4 27.4-3.6 3.6m34.6 0-3.6-3.6m-27.4-27.4-3.6-3.6" />
        <path d="M32 12.5v13m19.5 6.5h-13M32 51.5v-13M12.5 32h13m17.3-13.8-5.6 9.2m10.6 14.4-9.2-5.6m-14.4 10.6 5.6-9.2m-10.6-14.4 9.2 5.6" />
        <circle cx="32" cy="32" r="2" />
      </>}
      {game === 'slots' && <>
        <path d="M8 8h48v48H8zM24 8v48m16-48v48" />
        <text className="game-mark__number" x="16" y="39" textAnchor="middle">7</text>
        <text className="game-mark__number" x="32" y="39" textAnchor="middle">7</text>
        <text className="game-mark__number" x="48" y="39" textAnchor="middle">7</text>
      </>}
    </svg>
  )
}
