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
const actionLabels: { action: BlackjackAction; title: string; key: string }[] = [
  { action: 'hit', title: 'Взять карту', key: '1' },
  { action: 'stand', title: 'Остановиться', key: '2' },
  { action: 'double', title: 'Удвоить', key: '3' },
  { action: 'split', title: 'Разделить', key: '4' },
  { action: 'surrender', title: 'Сдаться', key: '5' },
]
const handStatus: Record<string, string> = {
  playing: 'Твой ход', standing: 'Ждёт дилера', won: 'Победа', lost: 'Проигрыш',
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
  const betError = valid ? ''
    : !Number.isSafeInteger(amount) ? 'Укажи целое количество фишек.'
    : !canBet ? `Нужно не менее ${fmt(minimumEven)} фишек.`
    : amount < minimumEven ? `Минимальная ставка — ${fmt(minimumEven)}.`
    : amount > cap ? `Доступно для ставки: ${fmt(cap)} фишек.`
    : 'Для блэкджека нужна чётная ставка.'
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
    dealerSoft17: dealerSoft17Rule === 'hit' || dealerSoft17Rule === 'stand' ? dealerSoft17Rule : 'stand',
    blackjackPayout: ratioOr(ruleData?.blackjack_payout, '3:2'),
    insurancePayout: ratioOr(ruleData?.insurance_payout, '2:1'),
  }

  return <div className="blackjack-page">
    <header className="blackjack-page__heading">
      <div className="blackjack-page__heading-copy">
        <h1 className="blackjack-page__heading-title">Блэкджек</h1>
      </div>
    </header>

    <div className="blackjack-page__room-layout">
      <section className="blackjack-page__table" aria-label="Стол блэкджека">
        <div className="blackjack-page__dealer-area" role="group" aria-label={`Карты дилера${round?.dealer_score != null ? `, ${round.dealer_score} очков` : ''}`}>
          <div className="blackjack-page__area-label"><span>ДИЛЕР</span><strong>{round ? round.dealer_score ?? '?' : '—'}</strong></div>
          <div className={`blackjack-page__dealer-cards${round && round.dealer_cards.length > 5 ? ' blackjack-page__dealer-cards--long' : ''}`}>
            {round ? round.dealer_cards.map((card, index) => <PlayingCard key={`dealer-${index}-${card}`} card={card} />) : <div className="blackjack-page__empty-cards"><small>Дилер ждёт ставку</small></div>}
          </div>
        </div>
        <div className="blackjack-page__table-rules"><strong>БЛЭКДЖЕК · {tableRules.blackjackPayout}</strong><span>{tableRules.dealerSoft17 === 'hit' ? 'ДИЛЕР БЕРЁТ МЯГКИЕ 17' : 'ДИЛЕР ОСТАНАВЛИВАЕТСЯ НА 17'}</span></div>
        <div className={`blackjack-page__player-area${hands.length > 1 ? ' blackjack-page__player-area--split' : ''}`} role="group" aria-label="Руки игрока">
          {hands.length ? hands.map((hand, index) => {
            const current = round?.status === 'playing' && index === activeIndex
            return <div className={`blackjack-page__player-hand${current ? ' blackjack-page__player-hand--active' : ''}`} key={index} role="group" aria-label={`Рука ${index + 1}, ${hand.score} очков, ставка ${hand.bet}${current ? ', ваш ход' : `, ${handStatus[hand.status] ?? hand.status}`}`}>
              <div className="blackjack-page__player-hand-title"><span>{hands.length > 1 ? `РУКА ${index + 1}` : 'ТВОЯ РУКА'}</span><strong>{hand.score}</strong></div>
              <div className={`blackjack-page__player-cards${hand.cards.length > 5 ? ' blackjack-page__player-cards--long' : ''}`}>{hand.cards.map((card, cardIndex) => <PlayingCard key={`${index}-${cardIndex}-${card}`} card={card} />)}</div>
            </div>
          }) : <div className="blackjack-page__betting-spot"><span>ПОСТАВЬ<br />ФИШКИ</span><strong>{valid ? fmt(amount) : '—'}</strong></div>}
        </div>
      </section>
      {round && !inRound && <div className={`blackjack-page__result-banner blackjack-page__result-banner--${round.status}`} role="status"><strong>{round.message}</strong>{latest && <span>Выплата {fmt(latest.payout)} · итог {latest.profit > 0 ? '+' : ''}{fmt(latest.profit)} фишек</span>}</div>}

      <aside className={`blackjack-page__console${inRound ? ' blackjack-page__console--playing' : ''}`} aria-label="Игровые действия">
        {inRound && <div className="blackjack-page__console-summary">
          <h2>{insurance ? 'Страховка' : hands.length > 1 ? `Рука ${activeIndex + 1} из ${hands.length}` : 'Твой ход'}</h2>
          {busy && <span className="blackjack-page__request-status" role="status">Выполняем ход…</span>}
          <div className="blackjack-page__stake-ledger"><span>Ставка</span><strong>{fmt(hands.reduce((total, hand) => total + hand.bet, 0) + (round.insurance_bet ?? 0))}</strong><small>фишек{(round.insurance_bet ?? 0) > 0 ? ' · включая страховку' : ''}</small></div>
        </div>}
        {inRound ? <>
          {insurance && <p className="blackjack-page__console-hint">У дилера туз. Страховка: {fmt(round.bet / 2)} фишек, выплата {tableRules.insurancePayout} при блэкджеке дилера.</p>}
          {insurance ? <div className="blackjack-page__insurance-actions">
            <button type="button" className="blackjack-page__decision blackjack-page__decision--primary" disabled={busy || !available.includes('insurance')} onClick={() => doAction('insurance')}><strong>Взять страховку</strong><kbd className="blackjack-page__decision-key">1</kbd></button>
            <button type="button" className="blackjack-page__decision" disabled={busy || !available.includes('decline_insurance')} onClick={() => doAction('decline_insurance')}><strong>Без страховки</strong><kbd className="blackjack-page__decision-key">2</kbd></button>
          </div> : <div className="blackjack-page__actions" role="group" aria-label="Действия блэкджека">{actionLabels.map(({ action, title, key }) => {
            const enabled = available.includes(action)
            if (!enabled) return null
            const hint = action === 'double' ? `+${fmt(active?.bet ?? round.bet)} · одна карта`
              : action === 'split' ? `+${fmt(active?.bet ?? round.bet)} · новая рука`
              : action === 'surrender' ? 'Возврат половины ставки' : ''
            return <button key={action} type="button" className={`blackjack-page__decision blackjack-page__decision--${action}${action === 'hit' ? ' blackjack-page__decision--primary' : ''}`} disabled={busy} onClick={() => doAction(action)}><span className="blackjack-page__decision-copy"><strong>{title}</strong>{hint && <small>{hint}</small>}</span><kbd className="blackjack-page__decision-key">{key}</kbd></button>
          })}</div>}
        </> : <form className="blackjack-page__bet-form" onSubmit={(event) => { event.preventDefault(); if (valid && !busy) startRound() }}>
          <div className="blackjack-page__bet-field">
            <label htmlFor="blackjack-wager">Ставка</label>
            <div className="blackjack-page__wager-input"><input id="blackjack-wager" type="number" min={minimumEven} max={maximumEven} step="2" inputMode="numeric" value={amount || ''} disabled={busy} onChange={(event) => onAmountChange(event.target.value)} aria-invalid={amount > 0 && !valid} aria-describedby="blackjack-bet-feedback" /><span>фишек</span></div>
          </div>
          <div className="blackjack-page__quick-bets">
            <div className="blackjack-page__chip-rack" aria-label="Добавить фишки">{[10, 20, 50, 100].map((value) => <button key={value} className="blackjack-page__chip-button" type="button" disabled={busy || !canBet} onClick={() => setChip(value)}>+{value}</button>)}</div>
            <div className="blackjack-page__bet-helpers"><button type="button" aria-label="Уменьшить ставку вдвое" disabled={busy || !canBet} onClick={() => scaleBet(.5)}>½</button><button type="button" aria-label="Увеличить ставку вдвое" disabled={busy || !canBet} onClick={() => scaleBet(2)}>×2</button></div>
          </div>
          <button className="game-action--primary blackjack-page__deal-button" type="submit" disabled={busy || !valid}>{busy ? 'Раздаём…' : 'Раздать карты'}</button>
          <div className="blackjack-page__bet-feedback" id="blackjack-bet-feedback" aria-live="polite">{betError && <span>{betError}</span>}<small>Доступно: {fmt(cap)} фишек · ставка чётным числом</small></div>
        </form>}
      </aside>
    </div>
  </div>
}
