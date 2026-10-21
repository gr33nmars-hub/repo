import type {
  BlackjackAction,
  CasinoState,
  GameId,
  PlayResponse,
  RouletteChoice,
} from '../types'
import { fairMutationPayload, requestMutation, slotMutationPayload } from './casino.commands'
import { requestApi } from './httpClient'

export const casinoApi = {
  state: () => requestApi<CasinoState>('/api/state'),
  play: (game: Exclude<GameId, 'blackjack'>, bet: number, choice = '', expectedServerSeedHash?: string) =>
    requestMutation<PlayResponse>(`play:${game}`, `/api/games/${game}/play`, game === 'slots'
      ? slotMutationPayload(bet, expectedServerSeedHash)
      : fairMutationPayload(bet, choice, expectedServerSeedHash)),
  startBlackjack: (bet: number, expectedServerSeedHash?: string) =>
    requestMutation<CasinoState>('blackjack:start', '/api/blackjack/start',
      fairMutationPayload(bet, '', expectedServerSeedHash)),
  blackjackAction: (action: BlackjackAction) =>
    requestMutation<CasinoState>(`blackjack:${action}`, '/api/blackjack/action', { action }),
  refill: () => requestMutation<{ balance: number }>('refill', '/api/refill', {}),
}

export type { RouletteChoice }
