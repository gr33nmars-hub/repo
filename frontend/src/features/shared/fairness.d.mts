import type { GameInfo, RoundResult } from '../../types'

export function verifyFairRound(
  round: RoundResult,
  game: GameInfo | undefined,
  commitment: string,
): Promise<boolean>
