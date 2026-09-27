import { useEffect, useMemo, useRef, useState } from 'react'
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
const deckWord = (count: number) => {
  const lastTwo = count % 100
  const last = count % 10
  if (last === 1 && lastTwo !== 11) return 'колода'
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return 'колоды'
  return 'колод'
}
const handWord = (count: number) => {
  const lastTwo = count % 100
  const last = count % 10
  if (last === 1 && lastTwo !== 11) return 'рука'
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return 'руки'
  return 'рук'
}
const actionLabels: { action: BlackjackAction; title: string; hint: string; symbol: string; key: string }[] = [
  { action: 'hit', title: 'Взять карту', hint: 'Продолжить руку', symbol: '+', key: '1' },
  { action: 'stand', title: 'Хватит', hint: 'Ход дилера', symbol: '■', key: '2' },
  { action: 'double', title: 'Удвоить', hint: 'Ещё одна карта', symbol: '×2', key: '3' },
  { action: 'split', title: 'Разделить', hint: 'Играть две руки', symbol: '↔', key: '4' },
  { action: 'surrender', title: 'Сдаться', hint: 'Вернуть половину', symbol: '½', key: '5' },
]
const handStatus: Record<string, string> = {
  playing: 'Твой ход', standing: 'Ожидает дилера', won: 'Победа', lost: 'Проигрыш',
  push: 'Ничья', bust: 'Перебор', surrendered: 'Сдача', blackjack: 'Блэкджек',
}
const ratioOr = (value: unknown, fallback: string) => typeof value === 'string' && /^\d+:\d+$/.test(value) ? value : fallback

export function BlackjackPage({ state, amount, minimum, maximum, busy, onAmountChange, onStart, onAction }: Props) {
  const [rulesOpen, setRulesOpen] = useState(false)
  const rulesTrigger = useRef<HTMLButtonElement>(null)
  const rulesClose = useRef<HTMLButtonElement>(null)
  const actionLock = useRef(false)
  useEffect(() => { if (!busy) actionLock.current = false }, [busy])
  useEffect(() => {
    if (!rulesOpen) return
    const trigger = rulesTrigger.current
    rulesClose.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setRulesOpen(false)
      if (event.key !== 'Tab') return

      const panel = document.getElementById('blackjack-rules-panel')
      const focusable = panel?.querySelectorAll<HTMLElement>('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
      if (!focusable?.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (!panel?.contains(document.activeElement)) {
        event.preventDefault()
        ;(event.shiftKey ? last : first).focus()
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
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
  const available = useMemo<BlackjackAction[]>(
    () => round?.available_actions ?? (inRound ? ['hit', 'stand', ...(round?.can_double ? ['double' as const] : [])] : []),
    [round?.available_actions, round?.can_double, inRound],
  )
  const doAction = (action: BlackjackAction) => {
    if (busy || actionLock.current || !available.includes(action)) return
    actionLock.current = true
    onAction(action)
  }
  const startRound = () => {
    if (busy || actionLock.current) return
    actionLock.current = true
    onStart()
  }
  useEffect(() => {
    const onShortcut = (event: KeyboardEvent) => {
      if (!inRound || busy || rulesOpen || event.repeat || event.altKey || event.ctrlKey || event.metaKey) return
      if (event.target instanceof HTMLElement && event.target.closest('input, textarea, select, button, [contenteditable]')) return
      const action = insurance
        ? event.key === '1' ? 'insurance' : event.key === '2' ? 'decline_insurance' : null
        : actionLabels.find((item) => item.key === event.key)?.action
      if (!action || !available.includes(action)) return
      event.preventDefault()
      if (actionLock.current) return
      actionLock.current = true
      onAction(action)
    }
    window.addEventListener('keydown', onShortcut)
    return () => window.removeEventListener('keydown', onShortcut)
  }, [available, busy, inRound, insurance, onAction, rulesOpen])
  const latest = !inRound ? state.history.find((item) => item.game_id === 'blackjack') : undefined
  const cap = Math.min(state.player.balance, maximum ?? state.player.balance)
  const minimumEven = minimum + minimum % 2
  const maximumEven = cap - cap % 2
  const canBet = maximumEven >= minimumEven
  const valid = Number.isSafeInteger(amount) && amount >= minimumEven && amount <= maximumEven && amount % 2 === 0
  const setChip = (value: number) => {
    const current = valid ? amount : 0
    onAmountChange(String(Math.min(maximumEven, Math.max(minimumEven, current + value))))
  }
  const scaleBet = (factor: number) => {
    const current = valid ? amount : minimumEven
    onAmountChange(String(Math.min(maximumEven, Math.max(minimumEven, Math.floor(current * factor / 2) * 2))))
  }
  const ruleData = round?.rules
  const beforeRound = !round
  const dealerSoft17Rule = ruleData?.dealer_soft_17
  const booleanRule = (value: unknown, defaultValue: boolean) => typeof value === 'boolean' ? value : beforeRound ? defaultValue : null
  const tableRules = {
    decks: typeof ruleData?.decks === 'number' && ruleData.decks > 0 ? ruleData.decks : beforeRound ? 6 : null,
    dealerSoft17: dealerSoft17Rule === 'hit' || dealerSoft17Rule === 'stand' ? dealerSoft17Rule : beforeRound ? 'stand' : null,
    blackjackPayout: ratioOr(ruleData?.blackjack_payout, beforeRound ? '3:2' : ''),
    insurancePayout: ratioOr(ruleData?.insurance_payout, beforeRound ? '2:1' : ''),
    maxHands: typeof ruleData?.max_hands === 'number' && Number.isSafeInteger(ruleData.max_hands) && ruleData.max_hands > 0 ? ruleData.max_hands : beforeRound ? 4 : null,
    doubleAllowed: booleanRule(ruleData?.double_allowed, true),
    doubleAfterSplit: booleanRule(ruleData?.double_after_split, true),
    splitAcesOneCard: booleanRule(ruleData?.split_aces_one_card, true),
    split21Stands: booleanRule(ruleData?.split_21_stands, true),
    lateSurrender: booleanRule(ruleData?.late_surrender, true),
  }
  const doubleCopy = tableRules.doubleAllowed === null
    ? 'Правило удвоения не получено'
    : !tableRules.doubleAllowed
      ? 'Недоступно на этом столе'
      : `На первых двух картах${tableRules.doubleAfterSplit === null ? '; правило для рук после разделения не получено' : tableRules.doubleAfterSplit ? ', включая руки после разделения' : ', кроме рук после разделения'}`

  return <div className="blackjack-page">
    <header className="blackjack-heading">
      <button ref={rulesTrigger} type="button" className="blackjack-rules-trigger" aria-label="Правила стола" aria-expanded={rulesOpen} aria-controls="blackjack-rules-panel" onClick={() => setRulesOpen(true)}>ⓘ <span>Правила стола</span></button>
    </header>

    <div className="blackjack-room-layout">
      <section className="blackjack-table" aria-label="Стол блэкджека">
        <div className="blackjack-table-topline"><span>NOIR</span><strong>СТОЛ 01 <i>·</i> БЛЭКДЖЕК</strong><span>{tableRules.decks === null ? '—' : `${tableRules.decks} ${deckWord(tableRules.decks).toLocaleUpperCase('ru-RU')}`}</span></div>
        <div className="blackjack-dealer-area" role="group" aria-label={`Карты дилера${round?.dealer_score != null ? `, ${round.dealer_score} очков` : ''}`}>
          <div className="blackjack-area-label"><span>ДИЛЕР</span><strong>{round ? round.dealer_score ?? '?' : '—'}</strong></div>
          <div className={`blackjack-dealer-cards${round && round.dealer_cards.length > 5 ? ' is-long' : ''}`}>
            {round ? round.dealer_cards.map((card, index) => <PlayingCard key={`dealer-${index}-${card}`} card={card} animate order={index} />) : <div className="blackjack-empty-cards"><span>♠</span><small>Дилер ждёт ставку</small></div>}
          </div>
        </div>
        <div className="blackjack-felt-arc" aria-hidden="true"><div className="blackjack-felt-legend"><strong>БЛЭКДЖЕК · {tableRules.blackjackPayout || '—'}</strong><span>{tableRules.dealerSoft17 === 'hit' ? 'ДИЛЕР БЕРЁТ МЯГКИЕ 17' : tableRules.dealerSoft17 === 'stand' ? 'ДИЛЕР СТОИТ НА ЛЮБЫХ 17' : 'ПРАВИЛО МЯГКОЙ 17 НЕ ПОЛУЧЕНО'}</span></div></div>
        <div className={`blackjack-player-area${hands.length > 1 ? ' has-split' : ''}`} role="group" aria-label="Руки игрока">
          {hands.length ? hands.map((hand, index) => {
            const current = round?.status === 'playing' && index === activeIndex
            return <div className={`blackjack-player-hand${current ? ' is-active' : ''}`} key={index} role="group" aria-label={`Рука ${index + 1}, ${hand.score} очков, ставка ${hand.bet}${current ? ', ваш ход' : `, ${handStatus[hand.status] ?? hand.status}`}`}>
              <div className="blackjack-player-hand-title"><span>{hands.length > 1 ? `РУКА ${index + 1}` : 'ТВОЯ РУКА'}</span><strong>{hand.score}</strong></div>
              <div className={`blackjack-player-cards${hand.cards.length > 5 ? ' is-long' : ''}`}>{hand.cards.map((card, cardIndex) => <PlayingCard key={`${index}-${cardIndex}-${card}`} card={card} animate order={cardIndex} />)}</div>
              <div className="blackjack-hand-base"><span className="blackjack-bet-chip">{fmt(hand.bet)}</span><span className="blackjack-hand-outcome">{current ? 'ТВОЙ ХОД' : hand.status === 'playing' ? 'ОЖИДАЕТ' : (handStatus[hand.status] ?? hand.message ?? hand.status).toUpperCase()}</span></div>
            </div>
          }) : <div className="blackjack-betting-spot"><span>ПОСТАВЬ<br />ФИШКИ</span><strong>{valid ? fmt(amount) : '—'}</strong></div>}
        </div>
      </section>
      {round && !inRound && <div className={`blackjack-result-banner is-${round.status}`} role="status"><strong>{round.message}</strong>{latest && <span>Выплата {fmt(latest.payout)} · итог {latest.profit > 0 ? '+' : ''}{fmt(latest.profit)} фишек</span>}</div>}

      <aside className={`blackjack-console${inRound ? ' is-playing' : ''}`} aria-label="Игровые действия">
        {inRound ? <div className="blackjack-console-summary">
          <h2>{insurance ? 'Страховка?' : `Рука ${activeIndex + 1} · ${active?.score ?? round?.player_score} очков`}</h2>
          {insurance && <p className="blackjack-console-hint">У дилера туз. Страховка стоит половину ставки и платит {tableRules.insurancePayout || 'по правилам стола'} при блэкджеке дилера.</p>}
          <div className="blackjack-stake-ledger"><span>Ставка</span><strong>{fmt(hands.reduce((total, hand) => total + hand.bet, 0) + (round.insurance_bet ?? 0))}</strong><small>фишек{(round.insurance_bet ?? 0) > 0 ? ' · включая страховку' : ''}</small></div>
        </div> : <div className="blackjack-console-summary">
          <h2>{round ? 'Следующий раунд' : 'Ставка'}</h2>
        </div>}
        {inRound ? <>
          {insurance ? <div className="blackjack-insurance-actions">
            <button type="button" className="blackjack-decision is-primary" disabled={busy || !available.includes('insurance')} onClick={() => doAction('insurance')}><span className="blackjack-decision-key">1</span><strong>Взять страховку</strong><small>+{fmt(round.bet / 2)} фишек</small></button>
            <button type="button" className="blackjack-decision" disabled={busy || !available.includes('decline_insurance')} onClick={() => doAction('decline_insurance')}><span className="blackjack-decision-key">2</span><strong>Без страховки</strong><small>Продолжить</small></button>
          </div> : <div className="blackjack-actions" role="group" aria-label="Действия блэкджека">{actionLabels.map(({ action, title, hint, symbol, key }) => {
            const enabled = available.includes(action)
            if (!enabled) return null
            return <button key={action} type="button" className={`blackjack-decision action-${action}${action === 'hit' ? ' is-primary' : ''}`} disabled={busy} onClick={() => doAction(action)}><span className="blackjack-decision-icon" aria-hidden="true">{symbol}</span><span className="blackjack-decision-copy"><strong>{title}</strong><small>{hint}</small></span><kbd className="blackjack-decision-key">{key}</kbd></button>
          })}</div>}
        </> : <form className="blackjack-bet-form" onSubmit={(event) => { event.preventDefault(); if (valid && !busy) startRound() }}>
          <label htmlFor="blackjack-wager">Размер ставки</label>
          <div className="blackjack-wager-input"><input id="blackjack-wager" type="number" min={minimumEven} max={maximumEven} step="2" inputMode="numeric" value={amount || ''} onChange={(event) => onAmountChange(event.target.value)} aria-invalid={amount > 0 && !valid} /><span>ФИШЕК</span></div>
          <div className="blackjack-chip-rack" aria-label="Добавить фишки">{[10, 20, 50, 100].map((value) => <button key={value} className="blackjack-chip-button" type="button" disabled={busy || !canBet} onClick={() => setChip(value)}>+{value}</button>)}</div>
          <div className="blackjack-bet-helpers"><button type="button" aria-label="Уменьшить ставку вдвое" disabled={busy || !canBet} onClick={() => scaleBet(.5)}>½</button><button type="button" aria-label="Увеличить ставку вдвое" disabled={busy || !canBet} onClick={() => scaleBet(2)}>×2</button><span>Баланс {fmt(state.player.balance)}</span></div>
          <p className={`blackjack-bet-feedback${valid ? '' : ' is-error'}`} aria-live="polite">{valid ? '' : !canBet ? `Нужно не менее ${fmt(minimumEven)} фишек` : amount < minimumEven ? `Минимальная ставка — ${fmt(minimumEven)}` : amount > maximumEven ? 'Ставка выше доступного баланса или лимита' : 'Ставка должна быть чётной'}</p>
          <button className="blackjack-deal-button" type="submit" disabled={busy || !valid}>{busy ? 'Раздаём…' : 'РАЗДАТЬ КАРТЫ'}<span aria-hidden="true">→</span></button>
        </form>}
      </aside>
    </div>

    {rulesOpen && <div className="blackjack-rules-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setRulesOpen(false) }}><section id="blackjack-rules-panel" className="blackjack-rules-panel" role="dialog" aria-modal="true" aria-labelledby="blackjack-rules-title" aria-describedby="blackjack-rules-intro"><button ref={rulesClose} className="blackjack-rules-close" type="button" aria-label="Закрыть правила" onClick={() => setRulesOpen(false)}>×</button><span className="blackjack-kicker">NOIR / TABLE 01</span><h2 id="blackjack-rules-title" tabIndex={-1}>Правила стола</h2><p id="blackjack-rules-intro">Набери больше очков, чем дилер, не превысив 21. Туз считается за 1 или 11, картинки — за 10.</p><dl><div><dt>Колоды</dt><dd>{tableRules.decks === null ? 'Не получено' : `${tableRules.decks} ${deckWord(tableRules.decks)} по 52 карты`}</dd></div><div><dt>Блэкджек</dt><dd>{tableRules.blackjackPayout ? `Натуральные 21 выплачиваются ${tableRules.blackjackPayout}` : 'Выплата не получена'}</dd></div><div><dt>Дилер</dt><dd>{tableRules.dealerSoft17 === 'hit' ? 'Берёт до 16 и берёт мягкую 17' : tableRules.dealerSoft17 === 'stand' ? 'Берёт до 16 и стоит на любой 17, включая мягкую 17' : 'Правило мягкой 17 не получено'}</dd></div><div><dt>Страховка</dt><dd>{tableRules.insurancePayout ? `При тузе дилера: полставки, выплата ${tableRules.insurancePayout}` : 'Выплата страховки не получена'}</dd></div><div><dt>Разделение</dt><dd>{tableRules.maxHands === null ? 'Лимит рук не получен' : `До ${tableRules.maxHands} ${handWord(tableRules.maxHands)}`}{tableRules.splitAcesOneCard === true ? '; после разделения тузов — по одной карте' : tableRules.splitAcesOneCard === false ? '; правило для разделённых тузов не применяется' : '; правило для разделённых тузов не получено'}</dd></div><div><dt>Удвоение</dt><dd>{doubleCopy}</dd></div><div><dt>Сдача</dt><dd>{tableRules.lateSurrender === null ? 'Правило сдачи не получено' : tableRules.lateSurrender ? 'Поздняя сдача возвращает половину ставки' : 'Сдача недоступна на этом столе'}</dd></div></dl><p className="blackjack-rules-note">{tableRules.split21Stands === true ? '21 после разделения — обычная рука с выплатой как за обычную победу, не натуральный блэкджек; рука останавливается.' : tableRules.split21Stands === false ? '21 после разделения не останавливает руку автоматически и не считается натуральным блэкджеком.' : 'Правило 21 после разделения не получено.'} При равенстве ставка возвращается.</p></section></div>}
  </div>
}
