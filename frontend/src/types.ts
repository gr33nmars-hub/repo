export type GameId = 'slots' | 'roulette' | 'blackjack'
export type RouletteChoice = 'red' | 'black' | 'zero'
export type BlackjackStatus = 'insurance' | 'playing' | 'won' | 'lost' | 'push' | 'mixed'
export type BlackjackAction = 'hit' | 'stand' | 'double' | 'split' | 'surrender' | 'insurance' | 'decline_insurance'

export interface BlackjackPlayerHand {
  cards: string[]
  score: number
  bet: number
  status: string
  message?: string
  payout?: number
  doubled?: boolean
  surrendered?: boolean
  from_split?: boolean
}

export interface PlayerState {
  name: string
  balance: number
  rounds_played: number
  wins: number
  losses: number
  win_rate: number
  total_wagered: number
}

export interface GameInfo {
  id: GameId
  name: string
  minimum_bet: number
  maximum_bet?: number
  paytable?: { symbol: string; multiplier: number }[]
  pair_multiplier?: number
  theoretical_return_percent?: number
  reel_strips?: string[][]
}

export interface RoundResult {
  game_id: GameId
  game_name: string
  message: string
  bet: number
  payout: number
  profit: number
  details: string
  symbols?: string[]
  reel_stops?: number[]
  fairness?: {
    server_seed: string
    server_seed_hash: string
    client_seed: string
    nonce: number
  }
  played_at: string
}

export interface BlackjackState {
  bet: number
  player_cards: string[]
  dealer_cards: string[]
  player_score: number
  dealer_score: number | null
  status: BlackjackStatus
  message: string
  can_double: boolean
  hands?: BlackjackPlayerHand[]
  active_hand_index?: number | null
  available_actions?: BlackjackAction[]
  can_split?: boolean
  can_surrender?: boolean
  insurance_bet?: number
  insurance_payout?: number
  rules?: Record<string, unknown>
}

export interface CasinoState {
  player: PlayerState
  games: GameInfo[]
  history: RoundResult[]
  blackjack: BlackjackState | null
  slots_server_seed_hash?: string
}

export interface PlayResponse {
  result: RoundResult
  state: CasinoState
}
