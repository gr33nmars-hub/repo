export type GameId = 'slots' | 'roulette' | 'blackjack'
export type RouletteChoice = 'red' | 'black' | 'zero'
export type BlackjackStatus = 'playing' | 'won' | 'lost' | 'push'

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
}

export interface RoundResult {
  game_id: GameId
  game_name: string
  message: string
  bet: number
  payout: number
  profit: number
  details: string
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
}

export interface CasinoState {
  player: PlayerState
  games: GameInfo[]
  history: RoundResult[]
  blackjack: BlackjackState | null
}

export interface PlayResponse {
  result: RoundResult
  state: CasinoState
}
