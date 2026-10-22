import { useEffect, useRef, useState } from 'react'
import type { GameInfo, RoundResult } from '../../types'
import { BetControl } from '../shared/BetControl'
import { SlotSymbol } from './SlotSymbol'
import './slots.css'

interface SlotsPageProps {
  game: GameInfo
  balance: number
  amount: number
  busy: boolean
  blocked?: boolean
  initialRound?: RoundResult
  onBalanceHold: (balance: number | null) => void
  onAmountChange: (value: string) => void
  onPlay: () => Promise<RoundResult | null>
}

const stopDurations = [1350, 1650, 1950]
const minimumSpinTime = 650
const reelSpeed = 21

function wrappedIndex(index: number, length: number) {
  return ((index % length) + length) % length
}

function initialStops(strips: string[][], round?: RoundResult) {
  const symbols = roundSymbols(round ?? null)
  if (round?.reel_stops?.length === 3
    && (!symbols || round.reel_stops.every((stop, index) => strips[index][stop] === symbols[index]))) {
    return round.reel_stops
  }
  if (symbols) return symbols.map((symbol, index) => Math.max(0, strips[index].indexOf(symbol)))
  return ['🍋', '🔔', '🍒'].map((symbol, index) => Math.max(0, strips[index].indexOf(symbol)))
}

function roundSymbols(round: RoundResult | null): string[] | undefined {
  if (!round) return undefined
  if (round.symbols?.length === 3) return round.symbols
  const parsed = round.details.split(/\s*·\s*/u).filter(Boolean)
  return parsed.length === 3 ? parsed : undefined
}

function Reel({ strip, position, moving, onElement }: {
  strip: string[]
  position: number
  moving: boolean
  onElement: (element: HTMLDivElement | null) => void
}) {
  return <div className={`slots-page__reel-window${moving ? ' slots-page__reel-window--moving' : ''}`}>
    <div className="slots-page__reel-strip" ref={onElement} style={{ transform: `translate3d(0, calc(${-wrappedIndex(position, strip.length)} * var(--reel-cell-height)), 0)` }} aria-hidden="true">
      {Array.from({ length: strip.length + 4 }, (_, index) => (
        <span className="slots-page__reel-cell" key={index}><SlotSymbol value={strip[wrappedIndex(index - 1, strip.length)]} /></span>
      ))}
    </div>
  </div>
}

interface StopMotion {
  started: number
  from: number[]
  to: number[]
  result: RoundResult | null
}

export function SlotsPage({ game, balance, amount, busy, blocked = false, initialRound, onBalanceHold, onAmountChange, onPlay }: SlotsPageProps) {
  const strips = game.reel_strips?.length === 3 && game.reel_strips.every((strip) => strip.length > 0)
    ? game.reel_strips
    : null
  const [initialPositions] = useState(() => strips ? initialStops(strips, initialRound) : [0, 0, 0])
  const [requesting, setRequesting] = useState(false)
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState<RoundResult | null>(initialRound ?? null)
  const positionsRef = useRef(initialPositions)
  const reelsRef = useRef<Array<HTMLDivElement | null>>([])
  const requestLock = useRef(false)
  const frameRef = useRef<number | null>(null)
  const timerRef = useRef<number | null>(null)
  const finishTimerRef = useRef<number | null>(null)
  const spinStartedRef = useRef(0)
  const previousFrameRef = useRef(0)
  const stopRef = useRef<StopMotion | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
      if (timerRef.current !== null) clearTimeout(timerRef.current)
      if (finishTimerRef.current !== null) clearTimeout(finishTimerRef.current)
      onBalanceHold(null)
    }
  }, [onBalanceHold])

  function drawPositions(next: number[], moving: boolean[] = [false, false, false]) {
    positionsRef.current = next
    if (!strips) return
    next.forEach((position, index) => {
      const reel = reelsRef.current[index]
      if (!reel) return
      reel.style.transform = `translate3d(0, calc(${-wrappedIndex(position, strips[index].length)} * var(--reel-cell-height)), 0)`
      reel.parentElement?.classList.toggle('slots-page__reel-window--moving', moving[index])
    })
  }

  function finishSpin(motion: StopMotion) {
    if (!mountedRef.current || stopRef.current !== motion) return
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    if (finishTimerRef.current !== null) clearTimeout(finishTimerRef.current)
    drawPositions(motion.to)
    setResult(motion.result)
    setSpinning(false)
    onBalanceHold(null)
    requestLock.current = false
    stopRef.current = null
    frameRef.current = null
    finishTimerRef.current = null
  }

  function animate(now: number) {
    const motion = stopRef.current
    if (motion) {
      const next = motion.from.map((from, index) => {
        const t = Math.min(1, (now - motion.started) / stopDurations[index])
        return from + (motion.to[index] - from) * (1 - (1 - t) ** 3)
      })
      if (now - motion.started >= stopDurations[2]) {
        finishSpin(motion)
        return
      }
      drawPositions(next, stopDurations.map((duration) => now - motion.started < duration))
    } else {
      const elapsed = now - spinStartedRef.current
      const dt = Math.min(48, now - previousFrameRef.current)
      const acceleration = Math.min(1, elapsed / 280)
      const next = positionsRef.current.map((position) => position + reelSpeed * acceleration * dt / 1000)
      drawPositions(next, [true, true, true])
    }
    previousFrameRef.current = now
    frameRef.current = requestAnimationFrame(animate)
  }

  function settle(nextResult: RoundResult | null) {
    if (!mountedRef.current || !strips) return
    const symbols = roundSymbols(nextResult)
    const hasMatchingStops = nextResult?.reel_stops?.length === 3
      && nextResult.reel_stops.every((stop, index) => strips[index][stop] === symbols?.[index])
    const stops = hasMatchingStops
      ? nextResult.reel_stops!
      : symbols
        ? symbols.map((symbol, index) => {
          const reel = strips[index]
          const nextStop = Math.ceil(positionsRef.current[index])
          const matchingStops = reel.flatMap((value, stop) => value === symbol ? [stop] : [])
          return matchingStops.sort((left, right) =>
            wrappedIndex(left - nextStop, reel.length) - wrappedIndex(right - nextStop, reel.length),
          )[0] ?? wrappedIndex(Math.round(positionsRef.current[index]), reel.length)
        })
        : positionsRef.current.map((position, index) => wrappedIndex(Math.round(position), strips[index].length))
    const from = positionsRef.current.slice()
    const to = from.map((position, index) => {
      const length = strips[index].length
      return Math.ceil(position) + length + wrappedIndex(stops[index] - Math.ceil(position), length)
    })
    const motion = { started: performance.now(), from, to, result: nextResult }
    stopRef.current = motion
    finishTimerRef.current = window.setTimeout(() => finishSpin(motion), stopDurations[2] + 100)
    setRequesting(false)
  }

  async function playRound() {
    if (requestLock.current || busy || blocked || !strips) return
    requestLock.current = true
    setResult(null)
    setRequesting(true)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      try {
        const nextResult = await onPlay()
        if (mountedRef.current && nextResult) {
          const stops = nextResult.reel_stops ?? initialStops(strips, nextResult)
          drawPositions(stops)
          setResult(nextResult)
        }
      } finally {
        requestLock.current = false
        if (mountedRef.current) setRequesting(false)
      }
      return
    }
    onBalanceHold(balance)
    spinStartedRef.current = performance.now()
    previousFrameRef.current = spinStartedRef.current
    stopRef.current = null
    setSpinning(true)
    frameRef.current = requestAnimationFrame(animate)
    try {
      const nextResult = await onPlay()
      if (!mountedRef.current) return
      const remaining = Math.max(0, minimumSpinTime - (performance.now() - spinStartedRef.current))
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null
        settle(nextResult)
      }, remaining)
    } catch {
      settle(null)
    }
  }

  const paytable = game.paytable ?? []
  if (!strips) return <section className="game-unavailable" role="status">
    <h1>Барабаны недоступны</h1>
    <p>Не удалось загрузить правила слотов. Обнови игру и попробуй снова.</p>
  </section>

  const status = blocked ? 'Заверши раздачу блэкджека, чтобы играть в слоты.'
    : requesting ? 'Вращение…' : spinning ? 'Останавливаем барабаны…' : result?.message ?? ''

  return (
    <div className="slots-page">
      <header className="game-page-heading">
        <div>
          <h1>Слоты</h1>
        </div>
      </header>

      <div className="slots-page__layout">
        <section className={`slots-page__table${spinning ? ' slots-page__table--spinning' : ''}${requesting ? ' slots-page__table--requesting' : ''}${result?.profit && result.profit > 0 ? ' slots-page__table--winning' : ''}`} aria-label="Игровые барабаны">
          <div className="slots-page__machine">
            <div className="slots-page__reels" aria-live="off" aria-busy={requesting || spinning}>
              {[0, 1, 2].map((index) => <Reel key={index} strip={strips[index]} position={initialPositions[index]} moving={spinning} onElement={(element) => { reelsRef.current[index] = element }} />)}
              <div className="slots-page__payline" aria-hidden="true" />
            </div>
          </div>

          <div className="slots-page__machine-status" role="status" aria-live="polite">{status}</div>
        </section>

        <aside className="slots-page__console" aria-label="Управление автоматом">
          <BetControl amount={amount} balance={balance} minimum={game.minimum_bet} maximum={game.maximum_bet} busy={busy || requesting || spinning} disabled={blocked} layout="slots" actionLabel="Крутить барабаны" onAmountChange={onAmountChange} onSubmit={() => void playRound()} />
          <section className="slots-page__last-round" aria-labelledby="slots-last-round-title">
            <h2 id="slots-last-round-title">Последний раунд</h2>
            <dl>
              <div><dt>Ставка</dt><dd>{result ? result.bet.toLocaleString('ru-RU') : '—'}</dd></div>
              <div><dt>Выплата</dt><dd>{result ? result.payout.toLocaleString('ru-RU') : '—'}</dd></div>
              <div className={`slots-page__last-round-row${result && result.profit > 0 ? ' slots-page__last-round-row--positive' : result && result.profit < 0 ? ' slots-page__last-round-row--negative' : ''}`}><dt>Итог</dt><dd>{result ? `${result.profit > 0 ? '+' : ''}${result.profit.toLocaleString('ru-RU')}` : '—'}</dd></div>
            </dl>
          </section>
        </aside>
      </div>

      <section className="slots-page__paytable" aria-label="Таблица выплат">
        <div className="slots-page__paytable-heading"><h2>Таблица выплат</h2></div>
        {paytable.length > 0 ? <div className="slots-page__payout-list">
          {paytable.map(({ symbol, multiplier }) => (
            <div className="slots-page__payout-item" key={symbol}>
              <div className={`slots-page__payout-symbols${symbol === '7️⃣' ? ' slots-page__payout-symbols--seven-triple' : ''}`} aria-hidden="true">
                {symbol === '7️⃣' ? <span className="slots-page__payout-seven">777</span> : <><SlotSymbol value={symbol} /><SlotSymbol value={symbol} /><SlotSymbol value={symbol} /></>}
              </div>
              <strong>×{multiplier}</strong>
            </div>
          ))}
          {typeof game.pair_multiplier === 'number' && <div className="slots-page__payout-item slots-page__payout-item--pair">
            <div className="slots-page__payout-symbols" aria-hidden="true"><SlotSymbol value="🍒" /><SlotSymbol value="🍒" /><SlotSymbol value="🍋" /></div>
            <span>Любая пара</span>
            <strong>×{game.pair_multiplier}</strong>
          </div>}
        </div> : <p className="slots-page__paytable-note">Таблица выплат недоступна.</p>}
      </section>
    </div>
  )
}
