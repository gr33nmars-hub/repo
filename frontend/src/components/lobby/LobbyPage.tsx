import blackjackImage from '../../../../assets/plates/blackjack-image.png'
import rouletteImage from '../../../../assets/plates/roulette-image.png'
import slotsImage from '../../../../assets/plates/slots-image.png'
import type { CasinoState, GameId } from '../../types'
import { Icon } from '../shell/Icon'
import { GameMark } from '../shell/GameMark'
import type { RoomRoute } from '../shell/AppShell'

const gameDetails: Record<GameId, {
  description: string
  experience: string
  image: string
}> = {
  blackjack: {
    description: 'Карты против дилера',
    experience: 'Набери 21 очко, не превысив.',
    image: blackjackImage,
  },
  roulette: {
    description: 'Европейское колесо 0–36',
    experience: 'Ставь на красное, чёрное или зеро.',
    image: rouletteImage,
  },
  slots: {
    description: 'Три барабана',
    experience: 'Собери выигрышную комбинацию.',
    image: slotsImage,
  },
}

const gameOrder: GameId[] = ['blackjack', 'roulette', 'slots']

function roundTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(date)
}

interface LobbyPageProps {
  state: CasinoState
  onOpen: (room: RoomRoute) => void
  onRetry: () => void
}

export function LobbyPage({ state, onOpen, onRetry }: LobbyPageProps) {
  const { player, games, history } = state
  const latestRounds = history.slice(0, 4)
  const orderedGames = [...games].sort((left, right) => gameOrder.indexOf(left.id) - gameOrder.indexOf(right.id))

  return (
    <div className="lobby-page">
      <header className="lobby-heading">
        <h1>Лобби</h1>
        <p>Три зала. Одна атмосфера.</p>
      </header>

      {orderedGames.length ? (
        <section className="table-grid" id="table-registry" aria-label="Игровые залы">
          {orderedGames.map((game) => {
            const details = gameDetails[game.id]
            return details ? (
              <button className="table-entry" data-game={game.id} key={game.id} type="button" onClick={() => onOpen(game.id)}>
                <span className="table-entry-visual">
                  <img className="table-entry-image" src={details.image} alt="" />
                </span>
                <span className="table-entry-body">
                  <span className="table-entry-title-row">
                    <span className="table-entry-symbol"><GameMark className="table-entry-mark" game={game.id} /></span>
                    <span className="table-entry-heading">
                      <strong>{game.name}</strong>
                      <span>{details.description}</span>
                    </span>
                  </span>
                  <span className="table-entry-experience">{details.experience}</span>
                  <span className="table-limits">
                    <span className="table-limits-label">СТАВКА</span>
                    <strong>{game.maximum_bet === undefined
                      ? `от ${game.minimum_bet.toLocaleString('ru-RU')}`
                      : `${game.minimum_bet.toLocaleString('ru-RU')} – ${game.maximum_bet.toLocaleString('ru-RU')}`}</strong>
                    {game.maximum_bet === undefined && <small>Без верхнего лимита</small>}
                  </span>
                  <span className="table-entry-action">Войти<Icon name="arrow" /></span>
                </span>
              </button>
            ) : null
          })}
        </section>
      ) : (
        <div className="lobby-empty lobby-empty--tables" role="status">
          <strong>Столы не загрузились</strong>
          <button type="button" onClick={onRetry}>Повторить</button>
        </div>
      )}

      <div className="lobby-lower-grid">
        <section className="player-ledger" aria-labelledby="player-ledger-title">
          <h2 id="player-ledger-title">Твоя игра</h2>
          <dl className="ledger-stats">
            <div><dt>Раундов</dt><dd>{player.rounds_played.toLocaleString('ru-RU')}</dd></div>
            <div><dt>Побед</dt><dd>{player.wins.toLocaleString('ru-RU')} <small>· {player.win_rate}%</small></dd></div>
            <div><dt>Оборот</dt><dd>{player.total_wagered.toLocaleString('ru-RU')}</dd></div>
          </dl>
        </section>

        <section className="lobby-recent" aria-labelledby="recent-rounds-title">
          <div className="lobby-section-heading">
            <h2 id="recent-rounds-title">Последние раунды</h2>
            {history.length > 0 && <button type="button" onClick={() => onOpen('history')}>Вся история<Icon name="arrow" /></button>}
          </div>
          {latestRounds.length > 0 ? (
            <>
              <ol className="recent-round-list">
                {latestRounds.map((round, index) => (
                  <li key={`${round.played_at}-${index}`}>
                    <GameMark className="recent-round-mark" game={round.game_id} />
                    <span className="recent-round-copy"><strong>{round.message}</strong><small><span>{round.game_name}</span><time dateTime={round.played_at}>{roundTime(round.played_at)}</time></small></span>
                    <span className={`recent-round-profit${round.profit > 0 ? ' is-positive' : round.profit < 0 ? ' is-negative' : ''}`}>
                      {round.profit > 0 ? '+' : ''}{round.profit.toLocaleString('ru-RU')}
                    </span>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <div className="lobby-empty lobby-empty--history">
              <span>История пока пуста</span>
              <p>Завершённые раунды появятся здесь.</p>
              <button type="button" onClick={() => onOpen('blackjack')}>Открыть блэкджек<Icon name="arrow" /></button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
