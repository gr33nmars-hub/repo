import { useId } from 'react'

interface BetControlProps {
  amount: number
  balance: number
  minimum: number
  maximum?: number
  busy: boolean
  disabled?: boolean
  evenOnly?: boolean
  actionLabel: string
  onAmountChange: (value: string) => void
  onSubmit: () => void
}

export function BetControl({
  amount,
  balance,
  minimum,
  maximum,
  busy,
  disabled = false,
  evenOnly = false,
  actionLabel,
  onAmountChange,
  onSubmit
}: BetControlProps) {
  const inputId = useId()
  const feedbackId = useId()
  const available = Math.min(balance, maximum ?? balance)
  const increment = evenOnly ? Math.max(2, Math.ceil(minimum / 2) * 2) : Math.max(1, minimum)
  const valid = Number.isSafeInteger(amount)
    && amount >= minimum
    && amount <= available
    && (!evenOnly || amount % 2 === 0)

  let message = ''
  if (!Number.isSafeInteger(amount)) message = 'Укажите целое количество фишек'
  else if (amount < minimum) message = `Минимальная ставка — ${minimum.toLocaleString('ru-RU')}`
  else if (amount > balance) message = 'Недостаточно фишек на балансе'
  else if (maximum !== undefined && amount > maximum) message = `Максимальный лимит — ${maximum.toLocaleString('ru-RU')}`
  else if (evenOnly && amount % 2 !== 0) message = 'Для блэкджека ставка должна быть чётной'

  return (
    <form
      className="game-bet-control"
      onSubmit={(event) => {
        event.preventDefault()
        if (valid && !busy && !disabled) onSubmit()
      }}
    >
      <div className="game-bet-field">
        <label htmlFor={inputId}>Ставка</label>
        <div className="game-bet-input-wrap">
          <input
            id={inputId}
            type="number"
            inputMode="numeric"
            min={minimum}
            max={available}
            step={evenOnly ? 2 : 1}
            value={amount || ''}
            onChange={(event) => onAmountChange(event.target.value)}
            aria-describedby={feedbackId}
            aria-invalid={amount > 0 && !valid}
          />
          <span>фишек</span>
        </div>
      </div>
      <div className="game-bet-adjust" aria-label="Изменить ставку">
        <button
          type="button"
          aria-label={`Уменьшить ставку на ${increment}`}
          disabled={busy || amount <= 0}
          onClick={() => onAmountChange(String(Math.max(0, amount - increment)))}
        >
          −
        </button>
        <button
          type="button"
          aria-label={`Увеличить ставку на ${increment}`}
          disabled={busy || amount >= available}
          onClick={() => onAmountChange(String(Math.min(available, amount + increment)))}
        >
          +
        </button>
      </div>
      <div className="game-bet-note" id={feedbackId} aria-live="polite">
        {message && <span>{message}</span>}
        <small>Доступно: {available.toLocaleString('ru-RU')}</small>
      </div>
      <button className="game-action-primary" type="submit" disabled={busy || disabled || !valid}>
        {busy ? <><span className="game-button-progress" aria-hidden="true" />Подождите…</> : actionLabel}
      </button>
    </form>
  )
}
