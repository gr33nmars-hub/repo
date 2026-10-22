import { useId } from 'react'

interface BetControlProps {
  amount: number
  balance: number
  minimum: number
  maximum?: number
  busy: boolean
  disabled?: boolean
  evenOnly?: boolean
  layout?: 'roulette' | 'slots'
  actionLabel: string
  onAmountChange: (value: string) => void
  onSubmit: () => void
}

export function BetControl({ amount, balance, minimum, maximum, busy, disabled = false, evenOnly = false, layout, actionLabel, onAmountChange, onSubmit }: BetControlProps) {
  const inputId = useId()
  const feedbackId = useId()
  const available = Math.min(balance, maximum ?? balance)
  const interactionDisabled = busy || disabled
  const increment = evenOnly ? Math.max(2, Math.ceil(minimum / 2) * 2) : Math.max(1, minimum)
  const valid = Number.isSafeInteger(amount)
    && amount >= minimum
    && amount <= available
    && (!evenOnly || amount % 2 === 0)

  let message = ''
  if (!Number.isSafeInteger(amount)) message = 'Укажи целое количество фишек.'
  else if (amount < minimum) message = `Минимальная ставка — ${minimum.toLocaleString('ru-RU')}.`
  else if (amount > balance) message = 'На балансе недостаточно фишек.'
  else if (maximum !== undefined && amount > maximum) message = `Максимальная ставка — ${maximum.toLocaleString('ru-RU')}.`
  else if (evenOnly && amount % 2 !== 0) message = 'Для блэкджека нужна чётная ставка.'

  return (
    <form className={`game-bet-control${layout ? ` game-bet-control--${layout}` : ''}`} onSubmit={(event) => { event.preventDefault(); if (valid && !busy && !disabled) onSubmit() }}>
      <div className="game-bet-control__field">
        <label htmlFor={inputId}>Ставка</label>
        <div className="game-bet-control__input-wrap">
          <input
            id={inputId}
            type="number"
            inputMode="numeric"
            min={minimum}
            max={available}
            step={evenOnly ? 2 : 1}
            value={amount || ''}
            disabled={interactionDisabled}
            onChange={(event) => onAmountChange(event.target.value)}
            aria-describedby={feedbackId}
            aria-invalid={amount > 0 && !valid}
          />
          <span>фишек</span>
        </div>
      </div>
      <div className="game-bet-control__adjust" aria-label="Изменить ставку">
        <button type="button" aria-label={`Уменьшить ставку на ${increment}`} disabled={interactionDisabled || amount <= 0} onClick={() => onAmountChange(String(Math.max(0, amount - increment)))}>−</button>
        <button type="button" aria-label={`Увеличить ставку на ${increment}`} disabled={interactionDisabled || amount >= available} onClick={() => onAmountChange(String(Math.min(available, amount + increment)))}>+</button>
      </div>
      <div className="game-bet-control__note" id={feedbackId} aria-live="polite">
        {message && <span>{message}</span>}
        <small>Доступно: {available.toLocaleString('ru-RU')}</small>
      </div>
      <button className="game-action--primary" type="submit" disabled={interactionDisabled || !valid}>
        {busy ? <><span className="game-action__progress" aria-hidden="true" />Запрос выполняется</> : actionLabel}
      </button>
    </form>
  )
}
