import type {
  BlackjackAction,
  CasinoState,
  GameId,
  PlayResponse,
  RouletteChoice,
} from '../types'
import { requestApi } from './httpClient'

export const casinoApi = {
  state: () => requestApi<CasinoState>('/api/state'),

  play: (game: Exclude<GameId, 'blackjack'>, bet: number, choice = '') =>
    requestApi<PlayResponse>(`/api/games/${game}/play`, {
      method: 'POST',
      body: JSON.stringify({ bet, choice }),
    }),

  startBlackjack: (bet: number) =>
    requestApi<CasinoState>('/api/blackjack/start', {
      method: 'POST',
      body: JSON.stringify({ bet }),
    }),

  blackjackAction: (action: BlackjackAction) =>
    requestApi<CasinoState>('/api/blackjack/action', {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  rotateSeed: () =>
    requestApi<{ status: string; revealed_previous_seed: string; new_server_seed_hash: string; state: CasinoState }>(
      '/api/fairness/rotate',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    ),

  refill: () =>
    requestApi<{ balance: number; state: CasinoState }>('/api/refill', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
}

export type { RouletteChoice }
