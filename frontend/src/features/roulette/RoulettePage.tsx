import { useEffect, useRef, useState } from 'react'
import type { GameInfo, RoundResult, RouletteChoice } from '../../types'
import { BetControl } from '../shared/BetControl'
import './roulette.css'

interface RoulettePageProps {
  game: GameInfo
  balance: number
  amount: number
  choice: RouletteChoice
  busy: boolean
  onAmountChange: (value: string) => void
  onChoice: (choice: RouletteChoice) => void
  onPlay: () => Promise<RoundResult | null>
}

const choices: { id: RouletteChoice; label: string; hue: string }[] = [
  { id: 'red', label: 'Красное', hue: 'red' },
  { id: 'black', label: 'Чёрное', hue: 'black' },
  { id: 'zero', label: 'Зеро', hue: 'zero' },
]

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function resultNumber(details: string) {
  const raw = details.split('·')[0]?.trim()
  const number = Number(raw)
  return Number.isInteger(number) && number >= 0 && number <= 36 ? String(number) : null
}

export function RoulettePage({ game, balance, amount, choice, busy, onAmountChange, onChoice, onPlay }: RoulettePageProps) {
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState<RoundResult | null>(null)
  const requestLock = useRef(false)
  const finishMotion = useRef<(() => void) | null>(null)

  useEffect(() => () => finishMotion.current?.(), [])

  async function playRound() {
    if (requestLock.current || busy) return
    requestLock.current = true
    setResult(null)
    setSpinning(true)
    const motionComplete = prefersReducedMotion()
      ? Promise.resolve()
      : new Promise<void>((resolve) => { finishMotion.current = resolve })

    try {
      const nextResult = await onPlay()
      if (!nextResult) {
        finishMotion.current?.()
        return
      }
      await motionComplete
      setResult(nextResult)
    } finally {
      finishMotion.current?.()
      finishMotion.current = null
      requestLock.current = false
      setSpinning(false)
    }
  }

  const pocket = result ? resultNumber(result.details) : null

  return (
    <div className="roulette-page">
      <header className="game-page-heading">
        <div><h1>{game.name}</h1><p>Европейское колесо: 0–36. Сервер принимает ставку на цвет или зеро.</p></div>
      </header>

      <section className="roulette-table" aria-label="Европейская рулетка">
        <div className={`roulette-dial${spinning ? ' is-spinning' : ''}`} aria-hidden="true" onAnimationEnd={() => finishMotion.current?.()}>
          <svg viewBox="0 0 220 220">
            <circle className="roulette-track" cx="110" cy="110" r="101" />
            {Array.from({ length: 37 }, (_, index) => <path className="roulette-tick" key={index} d="M110 14v11" transform={`rotate(${index * (360 / 37)} 110 110)`} />)}
            <circle className="roulette-hub-ring" cx="110" cy="110" r="72" />
            <circle className="roulette-hub" cx="110" cy="110" r="54" />
          </svg>
          <span className="roulette-ball" />
          <div className="roulette-hub-copy">
            <strong>{pocket ?? '0–36'}</strong>
            <span>{pocket === null ? 'ЕВРОПЕЙСКОЕ' : 'РЕЗУЛЬТАТ'}</span>
          </div>
        </div>

        <div className="roulette-betting">
          <h2>Выбери исход ставки</h2>
          <p>Доступные варианты соответствуют типам ставки игрового сервера.</p>
          <div className="roulette-choice-list" role="group" aria-label="Тип ставки рулетки">
            {choices.map((option) => (
              <button className={`roulette-choice roulette-choice--${option.hue}${choice === option.id ? ' is-selected' : ''}`} type="button" key={option.id} aria-pressed={choice === option.id} disabled={busy || spinning} onClick={() => onChoice(option.id)}>
                <span className="roulette-choice-marker" aria-hidden="true" />{option.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {result ? (
        <section className={`roulette-result${result.profit > 0 ? ' is-positive' : result.profit < 0 ? ' is-negative' : ''}`} aria-live="polite">
          <div className="roulette-result-number">{pocket ?? '—'}</div>
          <div className="roulette-result-copy"><strong>{result.message}</strong><span>{result.details}</span></div>
          <div className="roulette-result-money"><span>Выплата {result.payout.toLocaleString('ru-RU')}</span><strong>Итог {result.profit > 0 ? '+' : ''}{result.profit.toLocaleString('ru-RU')}</strong></div>
        </section>
      ) : spinning ? <p className="roulette-pending" role="status">Ждём подтверждённый исход от сервера</p> : null}

      <BetControl amount={amount} balance={balance} minimum={game.minimum_bet} maximum={game.maximum_bet} busy={busy || spinning} actionLabel="Сделать ставку" onAmountChange={onAmountChange} onSubmit={() => void playRound()} />
    </div>
  )
}
