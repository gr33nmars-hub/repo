interface CardFaceProps {
  card: string
}

export function CardFace({ card }: CardFaceProps) {
  if (card === 'hidden') {
    return <div className="playing-card playing-card--hidden" aria-label="Закрытая карта дилера">
      <span className="card-back-mark">N</span>
    </div>
  }
  const suit = card.slice(-1)
  const rank = card.slice(0, -1)
  const red = suit === '♥' || suit === '♦'
  return <div className={`playing-card ${red ? 'playing-card--red' : ''}`}>
    <span className="card-corner">{rank}<i>{suit}</i></span>
    <span className="card-center">{suit}</span>
    <span className="card-corner card-corner--bottom">{rank}<i>{suit}</i></span>
  </div>
}
