import { useEffect, useState } from 'react'
import type { GameInfo, RoundResult } from '../../types'
import { verifyFairRound } from './fairness.mjs'
import './fairness.css'

interface Props {
  commitment?: string
  round?: RoundResult
  game?: GameInfo
  commitmentLabel?: string
}

export function FairnessPanel({ commitment, round, game, commitmentLabel = 'Хеш следующего раунда' }: Props) {
  const [verification, setVerification] = useState<{
    round: RoundResult
    status: 'matched' | 'failed'
  } | null>(null)
  const status = !round?.fairness
    ? null
    : verification?.round === round
      ? verification.status
      : 'checking'

  useEffect(() => {
    let active = true
    if (!round?.fairness) return () => { active = false }
    void verifyFairRound(round, game, round.fairness.server_seed_hash)
      .then((valid) => { if (active) setVerification({ round, status: valid ? 'matched' : 'failed' }) })
      .catch(() => { if (active) setVerification({ round, status: 'failed' }) })
    return () => { active = false }
  }, [round, game])

  return <details className="fairness-panel">
    <summary>Сверка исхода {status === 'matched' ? '✓' : status === 'failed' ? '!' : ''}</summary>
    <p>{commitmentLabel}</p>
    <code>{commitment ?? 'Ожидаем commitment от backend'}</code>
    {round?.fairness ? <>
      <p>Статус backend</p>
      <p role="status">{round.verification_status === 'verified' ? 'Проверен backend'
        : round.verification_status === 'invalid' ? 'Проверка backend не пройдена'
          : round.verification_status === 'legacy-unverified' ? 'Старая запись без проверки backend'
            : 'Статус проверки backend не получен'}</p>
      <p>Раскрытый seed прошлого раунда</p><code>{round.fairness.server_seed}</code>
      <p>Объявленный хеш / client seed</p><code>{round.fairness.server_seed_hash}<br />{round.fairness.client_seed}</code>
      <p role="status">Браузерная сверка: {status === 'matched' ? round.game_id === 'blackjack'
        ? 'commitment, отпечаток правил и сохранённый порядок карт совпали с раскрытым seed.'
        : 'данные записи совпали с раскрытым seed и сохранёнными правилами.'
        : status === 'failed' ? 'данные записи не прошли сверку.' : 'проверяем…'}</p>
      {round.game_id === 'blackjack' && <p>Выплату blackjack проверил backend; браузерная сверка проверяет seed и порядок карт.</p>}
    </> : <p>После завершения раунда seed будет раскрыт, а данные останутся в истории.</p>}
    <p>Для сохранённого раунда хеш берётся из его записи; эта сверка сама по себе не доказывает, что хеш был опубликован до ставки. Локальная проверка также не доказывает честность исполняемого приложения.</p>
  </details>
}
