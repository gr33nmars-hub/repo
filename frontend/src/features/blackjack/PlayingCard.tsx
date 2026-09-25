import type { CSSProperties } from 'react'

interface PlayingCardProps {
  card: string
  animate?: boolean
  order?: number
}

const suitNames: Record<string, string> = { '♠': 'пики', '♥': 'черви', '♣': 'трефы', '♦': 'бубны' }

function SuitMark({ suit }: { suit: string }) {
  return (
    <svg className={`blackjack-card-suit${suit === '♥' || suit === '♦' ? ' is-red' : ''}`} viewBox="0 0 24 24" aria-hidden="true">
      {suit === '♠' && <><path d="M12 2.8C9.8 6 4 9.4 4 14a4.2 4.2 0 0 0 4.3 4.3c1.4 0 2.6-.6 3.7-2v4.9" /><path d="M12 2.8C14.2 6 20 9.4 20 14a4.2 4.2 0 0 1-4.3 4.3c-1.4 0-2.6-.6-3.7-2" /></>}
      {suit === '♥' && <path d="M12 21 4.4 13.5A5 5 0 0 1 11.5 6.4L12 7l.5-.6a5 5 0 0 1 7.1 7.1L12 21Z" />}
      {suit === '♣' && <><circle cx="12" cy="7" r="3.2" /><circle cx="7.2" cy="13" r="3.2" /><circle cx="16.8" cy="13" r="3.2" /><path d="m12 12.5-2.1 8m2.1-8 2.1 8m-4.2 0h4.2" /></>}
      {suit === '♦' && <path d="M12 2.8 20 12l-8 9.2L4 12l8-9.2Z" />}
    </svg>
  )
}

export function PlayingCard({ card, animate = false, order = 0 }: PlayingCardProps) {
  if (card === 'hidden') {
    return <div className="blackjack-card is-hidden" role="img" aria-label="Закрытая карта дилера"><span className="blackjack-card-back">N</span></div>
  }

  const suit = card.slice(-1)
  const rank = card.slice(0, -1)
  const name = `${rank} ${suitNames[suit] ?? 'карта'}`

  return (
    <div className={`blackjack-card${suit === '♥' || suit === '♦' ? ' is-red' : ''}${animate ? ' is-dealing' : ''}`} style={{ '--deal-order': order } as CSSProperties} role="img" aria-label={name}>
      <span className="blackjack-card-corner">{rank}<SuitMark suit={suit} /></span>
      <SuitMark suit={suit} />
      <span className="blackjack-card-corner is-inverted">{rank}<SuitMark suit={suit} /></span>
    </div>
  )
}
