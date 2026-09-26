import { useEffect, useRef, useState } from 'react'
import type { BlackjackAction, BlackjackPlayerHand, CasinoState } from '../../types'
import { PlayingCard } from './PlayingCard'
import './blackjack.css'

interface Props {
  state: CasinoState
  amount: number
  minimum: number
  maximum?: number
  busy: boolean
  onAmountChange: (value: string) => void
  onStart: () => void
  onAction: (action: BlackjackAction) => void
}

const fmt = (value: number) => value.toLocaleString('ru-RU')
const actionLabels: { action: BlackjackAction; title: string; hint: string; symbol: string }[] = [
  { action: 'hit', title: 'Взять', hint: 'Ещё карта', symbol: '+' },
  { action: 'stand', title: 'Хватит', hint: 'Оставить руку', symbol: '■' },
  { action: 'double', title: 'Удвоить', hint: 'Ставка ×2', symbol: '×2' },
  { action: 'split', title: 'Разделить', hint: 'Две руки', symbol: '↔' },
  { action: 'surrender', title: 'Сдаться', hint: 'Вернуть ½', symbol: '½' },
]
const handStatus: Record<string, string> = {
  playing: 'Твой ход', standing: 'Ожидает дилера', won: 'Победа', lost: 'Проигрыш',
  push: 'Ничья', bust: 'Перебор', surrendered: 'Сдача', blackjack: 'Блэкджек',
}

export function BlackjackPage({ state, amount, minimum, maximum, busy, onAmountChange, onStart, onAction }: Props) {
  const [rulesOpen, setRulesOpen] = useState(false)
  const rulesTrigger = useRef<HTMLButtonElement>(null)
  const rulesClose = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!rulesOpen) return
    const trigger = rulesTrigger.current
    rulesClose.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setRulesOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      trigger?.focus()
    }
  }, [rulesOpen])
  const round = state.blackjack
  const inRound = round?.status === 'playing' || round?.status === 'insurance'
  const insurance = round?.status === 'insurance'
  const hands: BlackjackPlayerHand[] = round?.hands?.length ? round.hands : round ? [{
    cards: round.player_cards, score: round.player_score, bet: round.bet, status: round.status, message: round.message,
  }] : []
  const activeIndex = round?.active_hand_index ?? 0
  const active = hands[activeIndex]
  const available = round?.available_actions ?? (inRound ? ['hit', 'stand', ...(round?.can_double ? ['double'] : [])] : [])
  const latest = !inRound ? state.history.find((item) => item.game_id === 'blackjack') : undefined
  const cap = Math.min(state.player.balance, maximum ?? state.player.balance)
  const valid = Number.isSafeInteger(amount) && amount >= minimum && amount <= cap && amount % 2 === 0
  const setChip = (value: number) => onAmountChange(String(Math.min(cap - cap % 2, Math.max(minimum, amount + value))))

  return <div className="blackjack-page">
    <header className="blackjack-heading">
      <div><span className="blackjack-kicker">ИГРОВОЙ СТОЛ / 01</span><h1>Блэкджек</h1><p>Шесть колод · классические правила · виртуальные фишки</p></div>
      <button ref={rulesTrigger} type="button" className="blackjack-rules-trigger" onClick={() => setRulesOpen(true)}>ⓘ <span>Правила стола</span></button>
    </header>

    <div className="blackjack-room-layout">
      <section className="blackjack-table" aria-label="Стол блэкджека">
        <div className="blackjack-table-rim" aria-hidden="true" />
        <div className="blackjack-table-topline"><span>NOIR</span><span>BLACKJACK · TABLE 01</span><span>6 DECKS</span></div>
        <div className="blackjack-dealer-area" aria-label="Карты дилера">
          <div className="blackjack-area-label"><span>ДИЛЕР</span><strong>{round ? round.dealer_score ?? 'ЗАКРЫТО' : '—'}</strong></div>
          <div className="blackjack-dealer-cards" aria-live="polite">
            {round ? round.dealer_cards.map((card, index) => <PlayingCard key={`dealer-${index}-${card}`} card={card} animate order={index} />) : <div className="blackjack-empty-cards"><span>♠</span><small>Дилер ждёт ставку</small></div>}
          </div>
        </div>
        <div className="blackjack-felt-arc" aria-hidden="true"><div className="blackjack-felt-legend"><strong>BLACKJACK PAYS 3 TO 2</strong><span>DEALER STANDS ON ALL 17s</span><span>INSURANCE PAYS 2 TO 1</span></div></div>
        <div className={`blackjack-player-area${hands.length > 1 ? ' has-split' : ''}`} aria-label="Руки игрока">
          {hands.length ? hands.map((hand, index) => {
            const current = round?.status === 'playing' && index === activeIndex
            return <div className={`blackjack-player-hand${current ? ' is-active' : ''}`} key={index} aria-label={`Рука ${index + 1}, ${hand.score} очков, ставка ${hand.bet}`}>
              <div className="blackjack-player-hand-title"><span>{hands.length > 1 ? `РУКА ${index + 1}` : 'ТВОЯ РУКА'}</span><strong>{hand.score}</strong></div>
              <div className="blackjack-player-cards">{hand.cards.map((card, cardIndex) => <PlayingCard key={`${index}-${cardIndex}-${card}`} card={card} animate order={cardIndex} />)}</div>
              <div className="blackjack-hand-base"><span className="blackjack-bet-chip">{fmt(hand.bet)}</span><span className="blackjack-hand-outcome">{current ? 'ТВОЙ ХОД' : hand.status === 'playing' ? 'ОЖИДАЕТ' : (handStatus[hand.status] ?? hand.message ?? hand.status).toUpperCase()}</span></div>
            </div>
          }) : <div className="blackjack-betting-spot"><span>ПОСТАВЬ<br />ФИШКИ</span><strong>{valid ? fmt(amount) : '—'}</strong></div>}
        </div>
        {round && !inRound && <div className={`blackjack-result-banner is-${round.status}`} role="status"><strong>{round.message}</strong>{latest && <span>Выплата {fmt(latest.payout)} · итог {latest.profit > 0 ? '+' : ''}{fmt(latest.profit)} фишек</span>}</div>}
        <div className="blackjack-table-bottomline"><span>MIN {fmt(minimum)}</span><span>NOIR CASINO CLUB</span><span>MAX {maximum ? fmt(maximum) : '—'}</span></div>
      </section>

      <aside className="blackjack-console" aria-label="Управление раздачей">
        <div className="blackjack-console-head"><span className="blackjack-kicker">{inRound ? 'РАЗДАЧА ИДЁТ' : 'СТАВКА НА РАЗДАЧУ'}</span><span className={`blackjack-live-dot${inRound ? ' is-live' : ''}`} /></div>
        <h2>{insurance ? 'Страховка?' : inRound ? `Рука ${activeIndex + 1} · твой ход` : round ? 'Играть ещё' : 'Твоя ставка'}</h2>
        <p className="blackjack-console-hint">{insurance ? 'У дилера туз. Страховка стоит половину ставки и платит 2:1 при блэкджеке дилера.' : inRound ? `${active?.score ?? round?.player_score} очков. Выбери действие для этой руки.` : round ? 'Раздача завершена. Сделай следующую ставку.' : 'Поставь фишки в круг и раздай карты.'}</p>
        {inRound ? <>
          <div className="blackjack-stake-ledger"><span>СТАВКА НА СТОЛЕ</span><strong>{fmt(hands.reduce((total, hand) => total + hand.bet, 0))}</strong><small>фишек</small></div>
          {insurance ? <div className="blackjack-insurance-actions">
            <button type="button" className="blackjack-decision is-primary" disabled={busy || !available.includes('insurance')} onClick={() => onAction('insurance')}><strong>Взять страховку</strong><small>Дополнительно {fmt(round.bet / 2)} фишек</small></button>
            <button type="button" className="blackjack-decision" disabled={busy || !available.includes('decline_insurance')} onClick={() => onAction('decline_insurance')}><strong>Без страховки</strong><small>Продолжить раздачу</small></button>
          </div> : <div className="blackjack-actions" role="group" aria-label="Действия блэкджека">{actionLabels.map(({ action, title, hint, symbol }) => <button key={action} type="button" className={`blackjack-decision action-${action}${action === 'hit' ? ' is-primary' : ''}`} disabled={busy || !available.includes(action)} onClick={() => onAction(action)}><span className="blackjack-decision-icon" aria-hidden="true">{symbol}</span><span><strong>{title}</strong><small>{hint}</small></span></button>)}</div>}
          <p className="blackjack-console-footnote">Доступные действия зависят от карт и баланса.</p>
        </> : <form className="blackjack-bet-form" onSubmit={(event) => { event.preventDefault(); if (valid && !busy) onStart() }}>
          <label htmlFor="blackjack-wager">РАЗМЕР СТАВКИ</label>
          <div className="blackjack-wager-input"><input id="blackjack-wager" type="number" min={minimum} max={cap} step="2" inputMode="numeric" value={amount || ''} onChange={(event) => onAmountChange(event.target.value)} aria-invalid={amount > 0 && !valid} /><span>ФИШЕК</span></div>
          <div className="blackjack-chip-rack" aria-label="Добавить фишки">{[10, 20, 50, 100].map((value) => <button key={value} className="blackjack-chip-button" type="button" disabled={busy || cap < minimum} onClick={() => setChip(value)}>+{value}</button>)}</div>
          <div className="blackjack-bet-helpers"><button type="button" disabled={busy} onClick={() => onAmountChange(String(minimum))}>МИН</button><button type="button" disabled={busy || cap < minimum} onClick={() => onAmountChange(String(cap - cap % 2))}>МАКС</button><span>Баланс: {fmt(state.player.balance)}</span></div>
          <p className={`blackjack-bet-feedback${valid ? '' : ' is-error'}`} aria-live="polite">{valid ? 'Чётная ставка для выплаты 3:2.' : amount < minimum ? `Минимум ${fmt(minimum)} фишек.` : amount > cap ? 'Недостаточно фишек или превышен лимит.' : 'Нужна чётная ставка.'}</p>
          <button className="blackjack-deal-button" type="submit" disabled={busy || !valid}>{busy ? 'Раздаём…' : 'РАЗДАТЬ КАРТЫ'}<span aria-hidden="true">→</span></button>
        </form>}
        {!inRound && round && <div className="blackjack-last-result"><span>ПРОШЛАЯ РАЗДАЧА</span><strong>{round.message}</strong></div>}
      </aside>
    </div>

    {rulesOpen && <div className="blackjack-rules-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setRulesOpen(false) }}><section className="blackjack-rules-panel" role="dialog" aria-modal="true" aria-labelledby="blackjack-rules-title"><button ref={rulesClose} className="blackjack-rules-close" type="button" aria-label="Закрыть правила" onClick={() => setRulesOpen(false)}>×</button><span className="blackjack-kicker">NOIR / TABLE 01</span><h2 id="blackjack-rules-title">Правила стола</h2><p>Набери больше очков, чем дилер, не превысив 21. Туз считается за 1 или 11, картинки — за 10.</p><dl><div><dt>Колоды</dt><dd>6 колод по 52 карты</dd></div><div><dt>Блэкджек</dt><dd>Натуральные 21 выплачиваются 3:2</dd></div><div><dt>Дилер</dt><dd>Берёт до 16, стоит на любом 17</dd></div><div><dt>Страховка</dt><dd>При тузе дилера: полставки, выплата 2:1</dd></div><div><dt>Разделение</dt><dd>До 4 рук; после разделения тузов по одной карте</dd></div><div><dt>Удвоение</dt><dd>На первых двух картах, включая руки после разделения</dd></div><div><dt>Сдача</dt><dd>Поздняя сдача возвращает половину ставки</dd></div></dl><p className="blackjack-rules-note">21 после разделения тузов — обычная рука. При равенстве ставка возвращается.</p></section></div>}
  </div>
}
