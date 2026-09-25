import { useEffect, useRef, useState, type CSSProperties } from 'react'
import type { GameInfo, RoundResult } from '../../types'
import { BetControl } from '../shared/BetControl'
import { SlotSymbol } from './SlotSymbol'
import './slots.css'

interface SlotsPageProps {
  game: GameInfo
  balance: number
  amount: number
  busy: boolean
  onAmountChange: (value: string) => void
  onPlay: () => Promise<RoundResult | null>
}

function parseSlotSymbols(details: string) {
  return details.split(/\s*·\s*/u).filter(Boolean)
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function SlotsPage({ game, balance, amount, busy, onAmountChange, onPlay }: SlotsPageProps) {
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

  const symbols = result ? parseSlotSymbols(result.details) : []

  return (
    <div className="slots-page">
      <header className="game-page-heading">
        <div><h1>{game.name}</h1><p>Три барабана. Символы и выплата приходят из результата раунда.</p></div>
      </header>

      <section className={`slots-table${spinning ? ' is-spinning' : ''}`} aria-label="Игровые барабаны">
        <div className="slots-table-edge" aria-hidden="true" />
        <div className="slots-brand">NOIR <span>СЛОТЫ</span></div>
        <div className="slots-reels" aria-live="polite" aria-busy={spinning}>
          {[0, 1, 2].map((index) => (
            <div className="slots-reel-window" key={index}>
              {spinning ? (
                <span className="slots-reel-motion" style={{ '--reel-order': index } as CSSProperties} onAnimationEnd={index === 2 ? () => finishMotion.current?.() : undefined} aria-hidden="true" />
              ) : symbols[index] ? (
                <SlotSymbol value={symbols[index]} />
              ) : (
                <span className="slots-reel-idle" aria-hidden="true">—</span>
              )}
            </div>
          ))}
        </div>
        <div className="slots-table-message" role="status">
          {result ? <><strong>{result.message}</strong><span>Раунд от {new Date(result.played_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</span></> : spinning ? <><strong>Барабаны остановятся после ответа сервера</strong><span>Результат не показывается до подтверждения раунда.</span></> : <><strong>Раунд ещё не запущен</strong><span>Выбери ставку, затем сервер определит комбинацию.</span></>}
        </div>
        {result && <div className={`slots-result${result.profit > 0 ? ' is-positive' : result.profit < 0 ? ' is-negative' : ''}`}>
          <span>Выплата <strong>{result.payout.toLocaleString('ru-RU')}</strong></span>
          <span>Итог <strong>{result.profit > 0 ? '+' : ''}{result.profit.toLocaleString('ru-RU')}</strong></span>
        </div>}
      </section>

      <BetControl amount={amount} balance={balance} minimum={game.minimum_bet} maximum={game.maximum_bet} busy={busy || spinning} actionLabel="Запустить барабаны" onAmountChange={onAmountChange} onSubmit={() => void playRound()} />
    </div>
  )
}
