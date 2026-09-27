import type { GameInfo, RoundResult } from '../../types'

export function verifySlotRound(
  round: RoundResult,
  game: GameInfo,
  announcedHash: string,
): Promise<boolean>
