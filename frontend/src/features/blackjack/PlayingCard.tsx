interface PlayingCardProps {
  card: string
}

const suitNames: Record<string, string> = { '♠': 'пики', '♥': 'черви', '♣': 'трефы', '♦': 'бубны' }
const suitPaths: Record<string, string> = {
  '♠': 'M12 1.5C9.8 5 3 9.2 3 13.5a5.1 5.1 0 0 0 9 3.3V20H8.5v2h7v-2H12v-3.2a5.1 5.1 0 0 0 9-3.3c0-4.3-6.8-8.5-9-12Z',
  '♥': 'M12 21.2 3.8 13C-.8 8.4 1.3 2 6.4 2c2.4 0 4.4 1.5 5.6 3.6C13.2 3.5 15.2 2 17.6 2c5.1 0 7.2 6.4 2.6 11L12 21.2Z',
  '♣': 'M12 2a4.4 4.4 0 0 0-3.5 7.1 4.5 4.5 0 1 0 2.5 7.4V20H8.5v2h7v-2H13v-3.5a4.5 4.5 0 1 0 2.5-7.4A4.4 4.4 0 0 0 12 2Z',
  '♦': 'M12 1.5 21 12l-9 10.5L3 12 12 1.5Z',
}

function SuitMark({ suit }: { suit: string }) {
  return (
    <svg className={`blackjack-page__card-suit${suit === '♥' || suit === '♦' ? ' blackjack-page__card-suit--red' : ''}`} viewBox="0 0 24 24" aria-hidden="true">
      {suitPaths[suit] && <path d={suitPaths[suit]} />}
    </svg>
  )
}

export function PlayingCard({ card }: PlayingCardProps) {
  if (card === 'hidden') {
    return <div className="blackjack-page__card blackjack-page__card--hidden" role="img" aria-label="Закрытая карта дилера"><span className="blackjack-page__card-back">NOIR</span></div>
  }

  const suit = card.slice(-1)
  const rank = card.slice(0, -1)
  const name = `${rank} ${suitNames[suit] ?? 'карта'}`

  return (
    <div className={`blackjack-page__card${suit === '♥' || suit === '♦' ? ' blackjack-page__card--red' : ''}`} role="img" aria-label={name}>
      <span className="blackjack-page__card-corner">{rank}<SuitMark suit={suit} /></span>
      <SuitMark suit={suit} />
      <span className="blackjack-page__card-corner blackjack-page__card-corner--inverted">{rank}<SuitMark suit={suit} /></span>
    </div>
  )
}
