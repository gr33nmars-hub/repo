export type GameId = 'slots' | 'roulette' | 'blackjack'
export type RouletteChoice = 'red' | 'black' | 'zero'
export type BlackjackStatus = 'insurance' | 'playing' | 'won' | 'lost' | 'push' | 'mixed'
export type BlackjackAction = 'hit' | 'stand' | 'double' | 'split' | 'surrender' | 'insurance' | 'decline_insurance'
export type BlackjackHandStatus = 'playing' | 'standing' | 'bust' | 'surrendered' | 'blackjack' | 'won' | 'lost' | 'push'

export interface FairnessProof {
  server_seed: string
  server_seed_hash: string
  client_seed: string
  nonce: number
}

export interface SlotOutcome {
  symbols: string[]
  reel_stops: number[]
}

export interface RouletteOutcome {
  number: number
  color: 'red' | 'black' | 'zero'
  choice: RouletteChoice
}

export interface BlackjackOutcome {
  round_id: string
  initial_bet: number
  dealer_cards: string[]
  hands: Array<{
    cards: string[]
    bet: number
    status: BlackjackHandStatus
    from_split: boolean
    doubled: boolean
    split_aces: boolean
  }>
  insurance_bet: number
  insurance_payout: number
  draw_order?: string[]
}

export interface BlackjackPlayerHand {
  cards: string[]
  score: number
  bet: number
  status: BlackjackHandStatus
  message: string
  from_split: boolean
  doubled: boolean
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
  maximum_bet: number
  paytable?: { symbol: string; multiplier: number }[] | null
  pair_multiplier?: number | null
  theoretical_return_percent?: number | null
  reel_strips?: string[][] | null
}

export interface RoundResult {
  game_id: GameId
  game_name: string
  message: string
  bet: number
  payout: number
  profit: number
  details: string
  symbols?: string[] | null
  reel_stops?: number[] | null
  fairness?: FairnessProof | null
  rule_version?: string | null
  rules_fingerprint?: string | null
  rules_snapshot?: Record<string, unknown> | null
  outcome?: SlotOutcome | RouletteOutcome | BlackjackOutcome | null
  verification_status?: 'verified' | 'invalid' | 'legacy-unverified' | null
  played_at: string
  round_id?: string | null
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
  hands: BlackjackPlayerHand[]
  active_hand_index: number
  available_actions: BlackjackAction[]
  can_split: boolean
  can_surrender: boolean
  insurance_bet: number
  insurance_payout: number
  rules: Record<string, unknown>
}

export interface CasinoState {
  player: PlayerState
  games: GameInfo[]
  history: RoundResult[]
  blackjack: BlackjackState | null
  slots_server_seed_hash?: string | null
  server_seed_hash?: string | null
}

export interface PlayResponse {
  result: RoundResult
  state: CasinoState
}
