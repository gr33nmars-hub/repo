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

function displayRoundMessage(message: string) {
  return message.replace('Тройка 7️⃣', 'Тройка 777')
}

function Reel({ strip, position, moving }: { strip: string[]; position: number; moving: boolean }) {
  const base = Math.floor(position)
  return <div className={`slots-reel-window${moving ? ' is-moving' : ''}`}>
    {Array.from({ length: 6 }, (_, offset) => {
      const stop = base - 2 + offset
      const symbol = strip[wrappedIndex(stop, strip.length)]
      return <span
        className={`slots-reel-cell${Math.abs(stop - position) < .5 ? ' is-center' : ''}`}
        key={stop}
        style={{ transform: `translate3d(0, ${(1 + stop - position) * 100}%, 0)` }}
        aria-hidden="true"
      ><SlotSymbol value={symbol} /></span>
    })}
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
  const [positions, setPositions] = useState(() => strips ? initialStops(strips, initialRound) : [0, 0, 0])
  const [requesting, setRequesting] = useState(false)
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState<RoundResult | null>(initialRound ?? null)
  const positionsRef = useRef(positions)
  const requestLock = useRef(false)
  const frameRef = useRef<number | null>(null)
  const timerRef = useRef<number | null>(null)
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
      onBalanceHold(null)
    }
  }, [onBalanceHold])

  function animate(now: number) {
    const motion = stopRef.current
    if (motion) {
      const next = motion.from.map((from, index) => {
        const t = Math.min(1, (now - motion.started) / stopDurations[index])
        return from + (motion.to[index] - from) * (1 - (1 - t) ** 3)
      })
      positionsRef.current = next
      setPositions(next)
      if (now - motion.started >= stopDurations[2]) {
        positionsRef.current = motion.to
        setPositions(motion.to)
        setResult(motion.result)
        setSpinning(false)
        onBalanceHold(null)
        requestLock.current = false
        stopRef.current = null
        frameRef.current = null
        return
      }
    } else {
      const elapsed = now - spinStartedRef.current
      const dt = Math.min(48, now - previousFrameRef.current)
      const acceleration = Math.min(1, elapsed / 280)
      const next = positionsRef.current.map((position) => position + reelSpeed * acceleration * dt / 1000)
      positionsRef.current = next
      setPositions(next)
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
    stopRef.current = { started: performance.now(), from, to, result: nextResult }
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
          positionsRef.current = stops
          setPositions(stops)
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
    <h1>Конфигурация барабанов недоступна</h1>
    <p>Сервер не передал правила этого стола. Обнови состояние перед игрой.</p>
  </section>

  const status = blocked
    ? 'Слоты недоступны, пока идёт раздача блэкджека'
    : result
    ? result.profit > 0 ? 'Выплата' : result.profit === 0 ? 'Ставка возвращена' : 'Нет выигрыша'
    : requesting ? 'Барабаны вращаются' : spinning ? 'Барабаны останавливаются' : 'Можно крутить'

  return (
    <div className="slots-page">
      <header className="game-page-heading slots-heading">
        <div>
          <h1>Слоты</h1>
          <p>Выигрыш определяется по центральной линии.</p>
        </div>
      </header>

      <div className="slots-layout">
        <section className={`slots-table${spinning ? ' is-spinning' : ''}${requesting ? ' is-requesting' : ''}${result?.profit && result.profit > 0 ? ' is-winning' : ''}`} aria-label="Игровые барабаны">
          <div className="slots-table-edge" aria-hidden="true" />
          <div className="slots-bulbs" aria-hidden="true">{Array.from({ length: 15 }, (_, index) => <i key={index} />)}</div>
          <div className="slots-machine">
            <div className="slots-reels" aria-live="off" aria-busy={requesting || spinning}>
              {[0, 1, 2].map((index) => <Reel key={index} strip={strips[index]} position={positions[index]} moving={spinning && (stopRef.current === null || performance.now() - stopRef.current.started < stopDurations[index])} />)}
              <div className="slots-payline" aria-hidden="true"><span>▶</span><span>◀</span></div>
            </div>
          </div>

          <div className="slots-machine-status" role="status" aria-live="polite">
            <span className="slots-status-light" aria-hidden="true" />
            <div><strong>{status}</strong>{result && <span>{displayRoundMessage(result.message)}</span>}</div>
          </div>
        </section>

        <aside className="slots-console" aria-label="Управление автоматом">
          <div className="slots-console-balance"><span>На счету</span><strong>{balance.toLocaleString('ru-RU')} <small>фишек</small></strong></div>
          <BetControl amount={amount} balance={balance} minimum={game.minimum_bet} maximum={game.maximum_bet} busy={busy || requesting || spinning} disabled={blocked} actionLabel="Крутить барабаны" onAmountChange={onAmountChange} onSubmit={() => void playRound()} />
          <div className="slots-console-divider" />
          <div className={`slots-last-round${result?.profit && result.profit > 0 ? ' is-positive' : ''}`}>
            <span className="slots-console-caption">ПОСЛЕДНИЙ РАУНД</span>
            {result ? <>
              <div><span>Выплата</span><strong>{result.payout.toLocaleString('ru-RU')}</strong></div>
              <div><span>Чистый итог</span><strong>{result.profit > 0 ? '+' : ''}{result.profit.toLocaleString('ru-RU')}</strong></div>
            </> : <p>Здесь появится итог после первого вращения.</p>}
          </div>
          <p className="slots-console-hint">Выплата определяется таблицей сочетаний.</p>
        </aside>
      </div>

      <section className="slots-paytable" aria-label="Таблица выплат">
        <div className="slots-paytable-heading"><h2>Таблица выплат</h2><span className="slots-paytable-rule">Учитывается центральная линия</span></div>
        {paytable.length > 0 ? <div className="slots-payout-list">
          {paytable.map(({ symbol, multiplier }) => (
            <div className="slots-payout-item" key={symbol}>
              <div className={`slots-payout-symbols${symbol === '7️⃣' ? ' is-seven-triple' : ''}`} aria-hidden="true">
                {symbol === '7️⃣' ? <span className="slots-payout-seven">777</span> : <><SlotSymbol value={symbol} /><SlotSymbol value={symbol} /><SlotSymbol value={symbol} /></>}
              </div>
              <strong>×{multiplier}</strong>
            </div>
          ))}
          {typeof game.pair_multiplier === 'number' && <div className="slots-payout-item slots-payout-item--pair">
            <div className="slots-payout-symbols" aria-hidden="true"><SlotSymbol value="🍒" /><SlotSymbol value="🍒" /><SlotSymbol value="🍋" /></div>
            <span>Любая пара</span>
            <small>Третий символ отличается</small>
            <strong>×{game.pair_multiplier}</strong>
          </div>}
        </div> : <p className="slots-paytable-note">Таблица выплат недоступна.</p>}
      </section>
    </div>
  )
}
