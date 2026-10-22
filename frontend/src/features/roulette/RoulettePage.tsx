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
  blocked?: boolean
  onAmountChange: (value: string) => void
  onChoice: (choice: RouletteChoice) => void
  onPlay: () => Promise<RoundResult | null>
  initialRound?: RoundResult
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

function resultNumber(round: RoundResult | null): number | null {
  if (round?.game_id !== 'roulette') return null
  const outcome = round.outcome
  const recorded = outcome && 'number' in outcome ? outcome.number : undefined
  if (typeof recorded === 'number' && Number.isInteger(recorded) && recorded >= 0 && recorded <= 36) return recorded
  if (!round) return null
  // Older saved rounds did not include a machine-readable roulette outcome.
  const details = round.details
  const match = /^\s*(\d{1,2})\s*·/.exec(details)
  const number = match ? Number(match[1]) : -1
  return Number.isInteger(number) && number >= 0 && number <= 36 ? number : null
}

function colorOf(number: number) {
  return number === 0 ? 'zero' : reds.has(number) ? 'red' : 'black'
}

export function RoulettePage({ game, balance, amount, choice, busy, blocked = false, onAmountChange, onChoice, onPlay, initialRound }: Props) {
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState<RoundResult | null>(initialRound ?? null)
  const rotor = useRef<SVGGElement>(null)
  const ball = useRef<SVGGElement>(null)
  const ballMarker = useRef<SVGCircleElement>(null)
  const frame = useRef<number | null>(null)
  const motionTimeout = useRef<number | null>(null)
  const angle = useRef(0)
  const ballAngle = useRef(0)
  const locked = useRef(false)
  const mounted = useRef(true)
  const finishMotion = useRef<(() => void) | null>(null)
  const firstNumber = useRef(resultNumber(initialRound ?? null))

  function draw(wheelDegrees: number, ballDegrees: number, radius = 144) {
    angle.current = wheelDegrees
    ballAngle.current = ballDegrees
    if (rotor.current) rotor.current.style.transform = `rotate(${wheelDegrees}deg)`
    if (ball.current) ball.current.style.transform = `rotate(${ballDegrees}deg)`
    ballMarker.current?.setAttribute('cy', String(160 - radius))
  }

  useEffect(() => {
    mounted.current = true
    if (firstNumber.current !== null) draw((360 - pockets.indexOf(firstNumber.current) * step) % 360, 0, 112)
    return () => {
      mounted.current = false
      if (frame.current !== null) cancelAnimationFrame(frame.current)
      if (motionTimeout.current !== null) clearTimeout(motionTimeout.current)
      finishMotion.current?.()
    }
  }, [])

  function freeSpin() {
    const started = performance.now()
    const firstWheel = angle.current
    const firstBall = ballAngle.current
    function tick(now: number) {
      const elapsed = now - started
      draw(firstWheel + elapsed * 0.3, firstBall - elapsed * 0.72)
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
    const distance = remaining + (remaining < 270 ? 360 : 0)
    const lastWheel = firstWheel + distance
    // Match the running wheel's velocity, then decelerate without a speed jump.
    const duration = 2 * distance / 0.3
    const pocketAngle = pockets.indexOf(number) * step
    const captureTime = duration * 0.82
    const firstRelative = firstBall - firstWheel - pocketAngle
    const relativeSpeed = -0.72 - 0.3
    const lastRelative = Math.round((firstRelative + relativeSpeed * captureTime / 2) / 360) * 360
    const relativeDistance = lastRelative - firstRelative
    const initialTangent = relativeSpeed * captureTime / relativeDistance
    const lastBall = lastWheel + pocketAngle + lastRelative
    const started = performance.now()

    if (document.hidden) {
      draw(lastWheel, lastBall, 112)
      return Promise.resolve()
    }

    return new Promise<void>((resolve) => {
      function complete() {
        if (frame.current !== null) cancelAnimationFrame(frame.current)
        if (motionTimeout.current !== null) clearTimeout(motionTimeout.current)
        frame.current = null
        motionTimeout.current = null
        finishMotion.current = null
        draw(lastWheel, lastBall, 112)
        resolve()
      }
      finishMotion.current = complete
      motionTimeout.current = window.setTimeout(complete, duration + 250)
      function tick(now: number) {
        const progress = Math.min(1, (now - started) / duration)
        const wheelDegrees = firstWheel + distance * (2 * progress - progress ** 2)
        const capture = Math.min(1, (now - started) / captureTime)
        const relativeProgress = (3 - 2 * capture) * capture ** 2
          + initialTangent * (capture ** 3 - 2 * capture ** 2 + capture)
        const ballDegrees = wheelDegrees + pocketAngle + firstRelative + relativeDistance * relativeProgress
        const drop = Math.min(1, Math.max(0, (progress - 0.58) / 0.24))
        // Once the ball reaches the pocket, it travels with that same sector.
        draw(wheelDegrees, ballDegrees, 144 - 32 * drop ** 2 * (3 - 2 * drop))
        if (progress < 1) frame.current = requestAnimationFrame(tick)
        else complete()
      }
      frame.current = requestAnimationFrame(tick)
    })
  }

  async function playRound() {
    if (locked.current || busy || blocked) return
    locked.current = true
    setResult(null)
    setSpinning(true)
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!reduced) freeSpin()

    try {
      const next = await onPlay()
      if (!mounted.current || !next) return
      const number = resultNumber(next)
      if (number !== null) {
        if (reduced) draw((360 - pockets.indexOf(number) * step) % 360, 0, 112)
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

  const number = resultNumber(result)
  const color = number === null ? null : colorOf(number)

  return (
    <div className="roulette-page">
      <header className="game-page-heading">
        <div><h1 className="game-page-heading__title">{game.name}</h1><p className="game-page-heading__description">Европейское колесо · одно зеро · 37 секторов</p></div>
      </header>

      <section className="roulette-page__table" aria-label="Игровой стол рулетки">
        <div className="roulette-page__wheel-stage">
          <div className="roulette-page__wheel" role="img" aria-label={spinning ? 'Колесо вращается' : number === null ? 'Колесо готово к игре' : `Шарик остановился на ${number}, ${color === 'zero' ? 'зеро' : color === 'red' ? 'красное' : 'чёрное'}`}>
            <svg className="roulette-page__wheel-art" viewBox="0 0 320 320" aria-hidden="true">
              <circle cx="160" cy="160" r="154" fill="#6b5b42" />
              <circle cx="160" cy="160" r="149" fill="#252923" />
              <g ref={rotor} className="roulette-page__rotor">
                {pockets.map((pocket, index) => (
                  <g key={pocket}>
                    <path d={sector(index)} className={`roulette-page__sector roulette-page__sector--${colorOf(pocket)}`} />
                    <text x="160" y="35" transform={`rotate(${index * step} 160 160)`} className="roulette-page__sector-number">{pocket}</text>
                  </g>
                ))}
                <circle cx="160" cy="160" r="105" fill="#36372c" />
                <path d="M160 114V206M114 160H206" stroke="#938261" strokeWidth="5" strokeLinecap="round" />
                <circle cx="160" cy="160" r="14" fill="#baa375" />
              </g>
              <g className="roulette-page__ball-orbit" ref={ball}><circle ref={ballMarker} className="roulette-page__ball" cx="160" cy="16" r="3.6" /></g>
            </svg>
          </div>
        </div>

        <div className="roulette-page__betting">
          <div className="roulette-page__betting-head"><h2>Исход ставки</h2><p>Выплата включает ставку.</p></div>
          <div className="roulette-page__choice-list" role="group" aria-label="Исход ставки">
            {choices.map((option) => (
              <button className={`roulette-page__choice roulette-page__choice--${option.id}${choice === option.id ? ' roulette-page__choice--selected' : ''}`} type="button" key={option.id} aria-pressed={choice === option.id} disabled={busy || blocked || spinning} onClick={() => onChoice(option.id)}>
                <span className="roulette-page__choice-chip" aria-hidden="true" />
                <span className="roulette-page__choice-copy"><strong>{option.label}</strong><small>{option.detail}</small></span>
                <span className="roulette-page__choice-odds">{option.odds}</span>
              </button>
            ))}
          </div>
          <BetControl amount={amount} balance={balance} minimum={game.minimum_bet} maximum={game.maximum_bet} busy={busy || spinning} disabled={blocked} layout="roulette" actionLabel="Крутить колесо" onAmountChange={onAmountChange} onSubmit={() => void playRound()} />
        </div>
      </section>

      <div className="roulette-page__outcome" aria-live="polite">
        {result ? (
          <section className={`roulette-page__result roulette-page__result--${color}${result.profit > 0 ? ' roulette-page__result--positive' : ''}`}>
            <span className="roulette-page__result-number">{number ?? '—'}</span>
            <div className="roulette-page__result-copy"><span>ПОСЛЕДНИЙ РАУНД</span><strong>{result.message}</strong><small>{result.details}</small></div>
            <div className="roulette-page__result-money"><span>Выплата {result.payout.toLocaleString('ru-RU')}</span><div><span>Итог</span><strong>{result.profit > 0 ? '+' : ''}{result.profit.toLocaleString('ru-RU')}</strong></div></div>
          </section>
        ) : <div className="roulette-page__ready" role="status">{blocked ? 'Заверши раздачу блэкджека, чтобы играть в рулетку.' : spinning ? 'Колесо вращается…' : ''}</div>}
      </div>

    </div>
  )
}
