import { useEffect, useMemo, useRef } from 'react'
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
  const actionLock = useRef(false)
  useEffect(() => { if (!busy) actionLock.current = false }, [busy])
  const round = state.blackjack
  const inRound = round?.status === 'playing' || round?.status === 'insurance'
  const insurance = round?.status === 'insurance'
  const hands: BlackjackPlayerHand[] = round?.hands ?? []
  const activeIndex = round?.active_hand_index ?? 0
  const active = hands[activeIndex]
  const available = useMemo<BlackjackAction[]>(
    () => round?.available_actions ?? [],
    [round?.available_actions],
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
      if (!inRound || busy || event.repeat || event.altKey || event.ctrlKey || event.metaKey) return
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
  }, [available, busy, inRound, insurance, onAction])
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
  const dealerSoft17Rule = ruleData?.dealer_soft_17
  const tableRules = {
    dealerSoft17: dealerSoft17Rule === 'hit' || dealerSoft17Rule === 'stand' ? dealerSoft17Rule : null,
    blackjackPayout: ratioOr(ruleData?.blackjack_payout, ''),
    insurancePayout: ratioOr(ruleData?.insurance_payout, ''),
  }

  return <div className="blackjack-page">
    <header className="blackjack-heading">
      <div className="blackjack-heading-copy">
        <h1>Блэкджек</h1>
      </div>
    </header>

    <div className="blackjack-room-layout">
      <section className="blackjack-table" aria-label="Стол блэкджека">
        <div className="blackjack-dealer-area" role="group" aria-label={`Карты дилера${round?.dealer_score != null ? `, ${round.dealer_score} очков` : ''}`}>
          <div className="blackjack-area-label"><span>ДИЛЕР</span><strong>{round ? round.dealer_score ?? '?' : '—'}</strong></div>
          <div className={`blackjack-dealer-cards${round && round.dealer_cards.length > 5 ? ' is-long' : ''}`}>
            {round ? round.dealer_cards.map((card, index) => <PlayingCard key={`dealer-${index}-${card}`} card={card} animate order={index} />) : <div className="blackjack-empty-cards"><span>♠</span><small>Дилер ждёт ставку</small></div>}
          </div>
        </div>
        <div className="blackjack-table-rules"><strong>БЛЭКДЖЕК · {tableRules.blackjackPayout || '—'}</strong><span>{tableRules.dealerSoft17 === 'hit' ? 'ДИЛЕР БЕРЁТ МЯГКИЕ 17' : tableRules.dealerSoft17 === 'stand' ? 'ДИЛЕР СТОИТ НА ЛЮБЫХ 17' : 'ПРАВИЛО МЯГКОЙ 17 НЕ ПОЛУЧЕНО'}</span></div>
        <div className={`blackjack-player-area${hands.length > 1 ? ' has-split' : ''}`} role="group" aria-label="Руки игрока">
          {hands.length ? hands.map((hand, index) => {
            const current = round?.status === 'playing' && index === activeIndex
            return <div className={`blackjack-player-hand${current ? ' is-active' : ''}`} key={index} role="group" aria-label={`Рука ${index + 1}, ${hand.score} очков, ставка ${hand.bet}${current ? ', ваш ход' : `, ${handStatus[hand.status] ?? hand.status}`}`}>
              <div className="blackjack-player-hand-title"><span>{hands.length > 1 ? `РУКА ${index + 1}` : 'ТВОЯ РУКА'}</span><strong>{hand.score}</strong></div>
              <div className={`blackjack-player-cards${hand.cards.length > 5 ? ' is-long' : ''}`}>{hand.cards.map((card, cardIndex) => <PlayingCard key={`${index}-${cardIndex}-${card}`} card={card} animate order={cardIndex} />)}</div>
            </div>
          }) : <div className="blackjack-betting-spot"><span>ПОСТАВЬ<br />ФИШКИ</span><strong>{valid ? fmt(amount) : '—'}</strong></div>}
        </div>
      </section>
      {round && !inRound && <div className={`blackjack-result-banner is-${round.status}`} role="status"><strong>{round.message}</strong>{latest && <span>Выплата {fmt(latest.payout)} · итог {latest.profit > 0 ? '+' : ''}{fmt(latest.profit)} фишек</span>}</div>}

      <aside className={`blackjack-console${inRound ? ' is-playing' : ''}`} aria-label="Игровые действия">
        {inRound ? <div className="blackjack-console-summary">
          <h2>{insurance ? 'Страховка?' : `Рука ${activeIndex + 1} · ${active?.score ?? round?.player_score} очков`}</h2>
          {insurance && <p className="blackjack-console-hint">У дилера туз. Страховка стоит половину ставки и платит {tableRules.insurancePayout || '—'} при блэкджеке дилера.</p>}
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
  </div>
}
