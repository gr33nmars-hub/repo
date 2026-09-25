import { CardFace } from '../CardFace'
import { HistoryList } from '../HistoryList'
import type { BlackjackState, CasinoState, GameId, RoundResult, RouletteChoice } from '../../types'

const roomCopy: Record<GameId, { eyebrow: string; title: string; description: string; icon: string }> = {
  blackjack: { eyebrow: 'BLACKJACK · TABLE 01', title: 'Здесь решают карты.', description: 'Бери карту, удваивай ставку или остановись. Дилер играет по классическим правилам.', icon: '♠' },
  slots: { eyebrow: 'NOIR SLOTS · VOL. 01', title: 'Поймай нужный ритм.', description: 'Три барабана, пять символов и один шанс собрать комбинацию.', icon: '✳' },
  roulette: { eyebrow: 'ROULETTE · TABLE 02', title: 'Последнее слово за шариком.', description: 'Красное, чёрное или зеро. Сделай ставку и смотри, где остановится колесо.', icon: '◉' },
}

interface WagerProps {
  bet: number
  balance: number
  minimumBet: number
  busy: boolean
  onChange: (value: string) => void
  onPlay: () => void
  label?: string
  evenOnly?: boolean
}

function Wager({ bet, balance, minimumBet, busy, onChange, onPlay, label = 'Сделать ставку', evenOnly = false }: WagerProps) {
  return <div className="wager-bar"><label className="wager-input"><span>СТАВКА</span><div><i>◉</i><input type="number" min={minimumBet} max={balance} step={evenOnly ? 2 : 10} value={bet || ''} onChange={(event) => onChange(event.target.value)} aria-label="Размер ставки" /><button type="button" aria-label="Увеличить ставку на 10" onClick={() => onChange(String(bet + 10))}>+</button></div></label><div className="wager-presets">{[50, 100, 250].map((amount) => <button key={amount} className={bet === amount ? 'preset-active' : ''} onClick={() => onChange(String(amount))}>{amount}</button>)}</div><button className="button-gold wager-submit" disabled={busy || bet < minimumBet || bet > balance || (evenOnly && bet % 2 !== 0)} onClick={onPlay}>{busy ? <span className="button-spinner" /> : label}<span>↗</span></button></div>
}

function GameHeading({ game }: { game: GameId }) {
  const copy = roomCopy[game]
  return <header className="room-heading"><div><span className="section-eyebrow">{copy.eyebrow}</span><h1>{copy.title}</h1><p>{copy.description}</p></div><span className={`room-stamp room-stamp--${game}`}>{copy.icon}</span></header>
}

interface BlackjackRoomProps {
  state: CasinoState
  bet: number
  minimumBet: number
  busy: boolean
  onBetChange: (value: string) => void
  onStart: () => void
  onAction: (action: 'hit' | 'stand' | 'double') => void
}

export function BlackjackRoom({ state, bet, minimumBet, busy, onBetChange, onStart, onAction }: BlackjackRoomProps) {
  const hand: BlackjackState | null = state.blackjack
  const active = hand?.status === 'playing'
  return <><GameHeading game="blackjack" /><section className="blackjack-felt"><div className="felt-glow" /><div className="felt-brand">NOIR <span>·</span> PRIVATE TABLE</div><div className="hand-zone hand-zone--dealer"><span className="hand-label">ДИЛЕР <i>{hand?.dealer_score ?? '—'}</i></span><div className="card-row">{hand ? hand.dealer_cards.map((card, index) => <CardFace key={`${card}-${index}`} card={card} />) : <><CardFace card="A♠" /><CardFace card="hidden" /></>}</div></div><div className="table-rule"><span>ПЛАТИТ 3:2</span><i>♠</i><span>ДИЛЕР ОСТАНАВЛИВАЕТСЯ НА 17</span></div><div className="hand-zone hand-zone--player"><span className="hand-label">ТВОЯ РУКА <i>{hand?.player_score ?? '—'}</i></span><div className="card-row">{hand ? hand.player_cards.map((card, index) => <CardFace key={`${card}-${index}`} card={card} />) : <span className="waiting-cards">Сделай ставку, чтобы начать раздачу</span>}</div></div>{hand && hand.status !== 'playing' && <div className={`hand-result hand-result--${hand.status}`}>{hand.message}</div>}</section><div className="blackjack-controls"><div className="control-copy"><span className="section-eyebrow">ХОД ИГРОКА</span><p>{active ? 'Решай: взять ещё одну карту или остановиться.' : hand ? 'Раунд завершён. Начни новый, когда будешь готов.' : 'Сделай ставку и получи две первые карты.'}</p></div>{active ? <div className="action-buttons"><button className="button-outline" disabled={busy} onClick={() => onAction('hit')}>Взять карту <span>＋</span></button><button className="button-outline" disabled={busy} onClick={() => onAction('stand')}>Хватит <span>✓</span></button><button className="button-outline button-double" disabled={busy || !hand.can_double || state.player.balance < hand.bet} onClick={() => onAction('double')}>Удвоить <span>×2</span></button></div> : <Wager bet={bet} balance={state.player.balance} minimumBet={minimumBet} busy={busy} onChange={onBetChange} onPlay={onStart} label={hand ? 'Новая раздача' : 'Раздать карты'} evenOnly />}</div><div className="payout-note"><span>i</span> Туз считается за 1 или 11. Блэкджек выплачивает 3:2, обычная победа 1:1. Ставка должна быть чётной.</div></>
}

interface InstantRoomProps {
  game: 'slots' | 'roulette'
  balance: number
  bet: number
  choice: RouletteChoice
  result?: RoundResult
  busy: boolean
  minimumBet: number
  onBetChange: (value: string) => void
  onChoice: (choice: RouletteChoice) => void
  onPlay: () => void
}

export function InstantRoom({ game, balance, bet, choice, result, busy, minimumBet, onBetChange, onChoice, onPlay }: InstantRoomProps) {
  return <><GameHeading game={game} />{game === 'slots' ? <section className="slots-machine"><div className="machine-top"><span>NOIR ORIGINALS</span><i>WIN UP TO ×15</i></div><div className={`reels ${busy ? 'reels--spinning' : ''}`}>{(result?.details.split('  ·  ') ?? ['♢', '♧', '♡']).map((symbol, index) => <div className="reel" key={`${symbol}-${index}`}><span>{symbol}</span></div>)}</div><div className="machine-message">{result ? <><strong>{result.message}</strong><span>{result.details}</span></> : <><strong>Три одинаковых символа.</strong><span>Собери комбинацию и забери выплату.</span></>}</div></section> : <section className="roulette-room"><div className={`roulette-wheel roulette-wheel--${choice}`}><div className="wheel-ring"><div className="wheel-ticks" /><div className="wheel-center"><strong>{result?.details.split(' · ')[0] ?? 'NOIR'}</strong><span>{result?.details.split(' · ')[1] ?? 'ROULETTE'}</span></div></div><span className="wheel-ball" /></div><div className="roulette-copy"><span className="section-eyebrow">ЕВРОПЕЙСКАЯ РУЛЕТКА</span><h2>{result?.details ?? 'Ставка на один из секторов'}</h2><p>На столе один зелёный сектор. Угадай его и получи выплату ×36.</p><div className="roulette-choices" role="group" aria-label="Выбор сектора"><button className={choice === 'red' ? 'choice-active' : ''} onClick={() => onChoice('red')}><i className="roulette-red" />Красное <span>×2</span></button><button className={choice === 'black' ? 'choice-active' : ''} onClick={() => onChoice('black')}><i className="roulette-black" />Чёрное <span>×2</span></button><button className={choice === 'zero' ? 'choice-active' : ''} onClick={() => onChoice('zero')}><i className="roulette-green" />Зеро <span>×36</span></button></div></div></section>}<Wager bet={bet} balance={balance} minimumBet={minimumBet} busy={busy} onChange={onBetChange} onPlay={onPlay} label={game === 'slots' ? 'Крутить барабаны' : 'Запустить шарик'} />{result && <div className={`game-result ${result.profit > 0 ? 'game-result--win' : result.profit < 0 ? 'game-result--loss' : ''}`}><span>{result.profit > 0 ? '✦' : result.profit < 0 ? '↘' : '↔'}</span><div><strong>{result.message}</strong><small>{result.details}</small></div><b>{result.profit > 0 ? '+' : ''}{result.profit.toLocaleString('ru-RU')} <i>◉</i></b></div>}</>
}

export function HistoryRoom({ state }: { state: CasinoState }) {
  return <><section className="room-heading"><div><span className="section-eyebrow">ТВОИ РАУНДЫ</span><h1>Память стола.</h1><p>Последние результаты и движение фишек.</p></div></section><section className="history-page-stats"><Stat label="ВСЕГО РАУНДОВ" value={String(state.player.rounds_played)} /><Stat label="ПОБЕДЫ" value={String(state.player.wins)} accent /><Stat label="ПОТЕРИ" value={String(state.player.losses)} /><Stat label="ОБОРОТ" value={state.player.total_wagered.toLocaleString('ru-RU')} /></section><section className="history-page-list"><div className="section-heading"><div><span className="section-eyebrow">АРХИВ · ПОСЛЕДНИЕ 12</span><h2>История игры</h2></div></div><HistoryList rounds={state.history} /></section></>
}

function Stat({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return <div className="stat-item"><span>{label}</span><strong className={accent ? 'stat-accent' : ''}>{value}</strong></div>
}
