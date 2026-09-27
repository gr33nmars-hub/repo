import { useEffect, useRef, useState } from 'react'
import type { GameInfo, RoundResult, RouletteChoice } from '../../types'
import { BetControl } from '../shared/BetControl'
import './roulette.css'

interface Props {
  game: GameInfo
  balance: number
  amount: number
  choice: RouletteChoice
  busy: boolean
  onAmountChange: (value: string) => void
  onChoice: (choice: RouletteChoice) => void
  onPlay: () => Promise<RoundResult | null>
}

// Clockwise order on a single-zero European wheel, starting at the pointer.
const pockets = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
const reds = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36])
const step = 360 / pockets.length
const choices: { id: RouletteChoice; label: string; odds: string; detail: string }[] = [
  { id: 'red', label: 'Красное', odds: '2×', detail: '18 чисел' },
  { id: 'black', label: 'Чёрное', odds: '2×', detail: '18 чисел' },
  { id: 'zero', label: 'Зеро', odds: '36×', detail: 'одно число' },
]

function point(radius: number, degrees: number) {
  const radians = degrees * Math.PI / 180
  return `${160 + radius * Math.sin(radians)} ${160 - radius * Math.cos(radians)}`
}

function sector(index: number) {
  const first = index * step - step / 2
  const last = first + step
  return `M ${point(136, first)} A 136 136 0 0 1 ${point(136, last)} L ${point(106, last)} A 106 106 0 0 0 ${point(106, first)} Z`
}

function resultNumber(details: string): number | null {
  const match = /^\s*(\d{1,2})\s*·/.exec(details)
  const number = match ? Number(match[1]) : -1
  return Number.isInteger(number) && number >= 0 && number <= 36 ? number : null
}

function colorOf(number: number) {
  return number === 0 ? 'zero' : reds.has(number) ? 'red' : 'black'
}

export function RoulettePage({ game, balance, amount, choice, busy, onAmountChange, onChoice, onPlay }: Props) {
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState<RoundResult | null>(null)
  const rotor = useRef<SVGGElement>(null)
  const ball = useRef<HTMLDivElement>(null)
  const frame = useRef<number | null>(null)
  const motionTimeout = useRef<number | null>(null)
  const angle = useRef(0)
  const ballAngle = useRef(0)
  const locked = useRef(false)
  const mounted = useRef(true)
  const finishMotion = useRef<(() => void) | null>(null)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      if (frame.current !== null) cancelAnimationFrame(frame.current)
      if (motionTimeout.current !== null) clearTimeout(motionTimeout.current)
      finishMotion.current?.()
    }
  }, [])

  function draw(wheelDegrees: number, ballDegrees: number) {
    angle.current = wheelDegrees
    ballAngle.current = ballDegrees
    if (rotor.current) rotor.current.style.transform = `rotate(${wheelDegrees}deg)`
    if (ball.current) ball.current.style.transform = `rotate(${ballDegrees}deg)`
  }

  function freeSpin() {
    const started = performance.now()
    const firstWheel = angle.current
    const firstBall = ballAngle.current
    function tick(now: number) {
      const elapsed = now - started
      draw(firstWheel + elapsed * 0.62, firstBall - elapsed * 0.95)
      frame.current = requestAnimationFrame(tick)
    }
    frame.current = requestAnimationFrame(tick)
  }

  function stopOn(number: number): Promise<void> {
    if (frame.current !== null) cancelAnimationFrame(frame.current)
    const firstWheel = angle.current
    const firstBall = ballAngle.current
    const desired = (360 - pockets.indexOf(number) * step) % 360
    const remaining = (desired - ((firstWheel % 360) + 360) % 360 + 360) % 360
    const lastWheel = firstWheel + 4 * 360 + remaining
    const lastBall = firstBall - 3 * 360 - (((firstBall % 360) + 360) % 360)
    const duration = 3600
    const started = performance.now()

    if (document.hidden) {
      draw(lastWheel, lastBall)
      return Promise.resolve()
    }

    return new Promise<void>((resolve) => {
      function complete() {
        if (frame.current !== null) cancelAnimationFrame(frame.current)
        if (motionTimeout.current !== null) clearTimeout(motionTimeout.current)
        frame.current = null
        motionTimeout.current = null
        finishMotion.current = null
        draw(lastWheel, lastBall)
        resolve()
      }
      finishMotion.current = complete
      motionTimeout.current = window.setTimeout(complete, duration + 250)
      function tick(now: number) {
        const progress = Math.min(1, (now - started) / duration)
        const eased = 1 - (1 - progress) ** 3
        draw(firstWheel + (lastWheel - firstWheel) * eased, firstBall + (lastBall - firstBall) * eased)
        if (progress < 1) frame.current = requestAnimationFrame(tick)
        else complete()
      }
      frame.current = requestAnimationFrame(tick)
    })
  }

  async function playRound() {
    if (locked.current || busy) return
    locked.current = true
    setResult(null)
    setSpinning(true)
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!reduced) freeSpin()

    try {
      const next = await onPlay()
      if (!mounted.current || !next) return
      const number = resultNumber(next.details)
      if (number !== null) {
        if (reduced) draw((360 - pockets.indexOf(number) * step) % 360, 0)
        else await stopOn(number)
      }
      if (mounted.current) setResult(next)
    } finally {
      if (frame.current !== null) cancelAnimationFrame(frame.current)
      if (motionTimeout.current !== null) clearTimeout(motionTimeout.current)
      frame.current = null
      motionTimeout.current = null
      finishMotion.current = null
      locked.current = false
      if (mounted.current) setSpinning(false)
    }
  }

  const number = result ? resultNumber(result.details) : null
  const color = number === null ? null : colorOf(number)

  return (
    <div className="roulette-page">
      <header className="game-page-heading roulette-heading">
        <div><span className="roulette-eyebrow">NOIR / СТОЛ 02</span><h1>{game.name}</h1><p>Европейское колесо · одно зеро · 37 секторов</p></div>
        <span className="roulette-table-id">ROULETTE / 01</span>
      </header>

      <section className="roulette-table" aria-label="Игровой стол рулетки">
        <div className="roulette-wheel-stage">
          <span className="roulette-stage-label">КОЛЕСО</span>
          <div className="roulette-wheel" role="img" aria-label={spinning ? 'Колесо вращается' : number === null ? 'Колесо готово к игре' : `Шарик остановился на ${number}, ${color === 'zero' ? 'зеро' : color === 'red' ? 'красное' : 'чёрное'}`}>
            <svg className="roulette-wheel-art" viewBox="0 0 320 320" aria-hidden="true">
              <defs>
                <radialGradient id="roulette-wood"><stop stopColor="#251b12" /><stop offset=".78" stopColor="#4a2b18" /><stop offset="1" stopColor="#191610" /></radialGradient>
                <radialGradient id="roulette-hub"><stop stopColor="#51412b" /><stop offset=".58" stopColor="#231e18" /><stop offset="1" stopColor="#a17c43" /></radialGradient>
              </defs>
              <circle cx="160" cy="160" r="157" fill="#0b100d" stroke="#aa8950" strokeWidth="3" />
              <circle cx="160" cy="160" r="148" fill="#393423" stroke="#c8a765" strokeWidth="3" />
              <circle cx="160" cy="160" r="140" fill="#0e1410" stroke="#66583d" strokeWidth="2" />
              <g ref={rotor} className="roulette-rotor">
                <circle cx="160" cy="160" r="136" fill="url(#roulette-wood)" />
                {pockets.map((pocket, index) => (
                  <g key={pocket}>
                    <path d={sector(index)} className={`roulette-sector roulette-sector--${colorOf(pocket)}`} />
                    <text x="160" y="42" transform={`rotate(${index * step} 160 160)`} className="roulette-sector-number">{pocket}</text>
                  </g>
                ))}
                <circle cx="160" cy="160" r="104" fill="url(#roulette-wood)" stroke="#b3945c" strokeWidth="4" />
                <circle cx="160" cy="160" r="83" fill="#11251b" stroke="#5d5034" strokeWidth="2" />
                {Array.from({ length: 8 }, (_, index) => <path key={index} d="M160 81 L160 126" transform={`rotate(${index * 45} 160 160)`} stroke="#a9854f" strokeWidth="3" />)}
                <circle cx="160" cy="160" r="35" fill="url(#roulette-hub)" stroke="#d0b378" strokeWidth="2" />
              </g>
            </svg>
            <div className="roulette-ball-orbit" ref={ball} aria-hidden="true"><span className="roulette-ball" /></div>
            <span className="roulette-pointer" aria-hidden="true" />
            <div className={`roulette-wheel-center${color ? ` roulette-wheel-center--${color}` : ''}`} aria-hidden="true">
              <strong>{spinning ? '•' : number ?? 'N'}</strong>
              <small>{spinning ? 'В ИГРЕ' : number === null ? 'NOIR' : 'ВЫПАЛО'}</small>
            </div>
          </div>
          <span className="roulette-stage-footer">EUROPEAN SINGLE ZERO</span>
        </div>

        <div className="roulette-betting">
          <div className="roulette-betting-head"><span>01 / СТАВКА НА ЦВЕТ</span><h2>Куда ставим?</h2><p>Выбери поле и запусти колесо. Выплата указана с учётом ставки.</p></div>
          <div className="roulette-choice-list" role="group" aria-label="Исход ставки">
            {choices.map((option) => (
              <button className={`roulette-choice roulette-choice--${option.id}${choice === option.id ? ' is-selected' : ''}`} type="button" key={option.id} aria-pressed={choice === option.id} disabled={busy || spinning} onClick={() => onChoice(option.id)}>
                <span className="roulette-choice-chip" aria-hidden="true" />
                <span className="roulette-choice-copy"><strong>{option.label}</strong><small>{option.detail}</small></span>
                <span className="roulette-choice-odds">{option.odds}</span>
              </button>
            ))}
          </div>
          <div className="roulette-selection"><span>ВЫБРАНО</span><strong>{choices.find((option) => option.id === choice)?.label}</strong><span>× {choice === 'zero' ? 36 : 2}</span></div>
        </div>
      </section>

      <div className="roulette-outcome" aria-live="polite">
        {result ? (
          <section className={`roulette-result roulette-result--${color}${result.profit > 0 ? ' is-positive' : ''}`}>
            <span className="roulette-result-number">{number ?? '—'}</span>
            <div className="roulette-result-copy"><span>ПОСЛЕДНИЙ СПИН</span><strong>{result.message}</strong><small>{result.details}</small></div>
            <div className="roulette-result-money"><span>Выплата {result.payout.toLocaleString('ru-RU')}</span><strong>{result.profit > 0 ? '+' : ''}{result.profit.toLocaleString('ru-RU')}</strong></div>
          </section>
        ) : <div className="roulette-ready" role="status"><span className={`roulette-ready-light${spinning ? ' is-active' : ''}`} />{spinning ? 'Шарик в игре. Ждём сектор…' : 'Стол открыт. Сделай ставку.'}</div>}
      </div>

      <BetControl amount={amount} balance={balance} minimum={game.minimum_bet} maximum={game.maximum_bet} busy={busy || spinning} actionLabel="Крутить колесо" onAmountChange={onAmountChange} onSubmit={() => void playRound()} />
    </div>
  )
}
