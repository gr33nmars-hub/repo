import blackjackImage from '../../assets/images/blackjack-image.png'
import rouletteImage from '../../assets/images/roulette-image.png'
import slotsImage from '../../assets/images/slots-image.png'
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
    experience: 'Набери больше очков, чем дилер, не переходя за 21.',
    image: blackjackImage,
  },
  roulette: {
    description: 'Европейское колесо 0–36',
    experience: 'Выбери красное, чёрное или зеро.',
    image: rouletteImage,
  },
  slots: {
    description: 'Три барабана',
    experience: 'Собери пару или три одинаковых символа.',
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
      <header className="lobby-page__heading">
        <h1>Лобби</h1>
        <p>Блэкджек, рулетка и слоты на виртуальные фишки.</p>
      </header>

      {orderedGames.length ? (
        <section className="lobby-page__table-grid" id="table-registry" aria-label="Игровые залы">
          {orderedGames.map((game) => {
            const details = gameDetails[game.id]
            return details ? (
              <button className="lobby-page__table-entry" data-game={game.id} key={game.id} type="button" onClick={() => onOpen(game.id)}>
                <span className="lobby-page__table-entry-visual">
                  <img className="lobby-page__table-entry-image" src={details.image} alt="" />
                </span>
                <span className="lobby-page__table-entry-body">
                  <span className="lobby-page__table-entry-title-row">
                    <span className="lobby-page__table-entry-symbol"><GameMark className="lobby-page__table-entry-mark" game={game.id} /></span>
                    <span className="lobby-page__table-entry-heading">
                      <strong>{game.name}</strong>
                      <span>{details.description}</span>
                    </span>
                  </span>
                  <span className="lobby-page__table-entry-experience">{details.experience}</span>
                  <span className="lobby-page__table-limits">
                    <span className="lobby-page__table-limits-label">СТАВКА</span>
                    <strong>{game.maximum_bet === undefined
                      ? `от ${game.minimum_bet.toLocaleString('ru-RU')}`
                      : `${game.minimum_bet.toLocaleString('ru-RU')} – ${game.maximum_bet.toLocaleString('ru-RU')}`}</strong>
                    {game.maximum_bet === undefined && <small>Без верхнего лимита</small>}
                  </span>
                  <span className="lobby-page__table-entry-action">Играть<Icon name="arrow" /></span>
                </span>
              </button>
            ) : null
          })}
        </section>
      ) : (
        <div className="lobby-page__empty lobby-page__empty--tables" role="status">
          <strong>Столы не загрузились</strong>
          <button type="button" onClick={onRetry}>Загрузить столы снова</button>
        </div>
      )}

      <div className="lobby-page__lower-grid">
        <section className="lobby-page__ledger" aria-labelledby="player-ledger-title">
          <h2 id="player-ledger-title">Твоя игра</h2>
          <dl className="lobby-page__ledger-stats">
            <div><dt>Раундов</dt><dd>{player.rounds_played.toLocaleString('ru-RU')}</dd></div>
            <div><dt>Побед</dt><dd>{player.wins.toLocaleString('ru-RU')} <small>· {player.win_rate}%</small></dd></div>
            <div><dt>Оборот</dt><dd>{player.total_wagered.toLocaleString('ru-RU')}</dd></div>
          </dl>
        </section>

        <section className="lobby-page__recent" aria-labelledby="recent-rounds-title">
          <div className="lobby-page__section-heading">
            <h2 id="recent-rounds-title">Последние раунды</h2>
            {history.length > 0 && <button type="button" onClick={() => onOpen('history')}>Вся история<Icon name="arrow" /></button>}
          </div>
          {latestRounds.length > 0 ? (
            <>
              <ol className="lobby-page__recent-round-list">
                {latestRounds.map((round, index) => (
                  <li key={`${round.played_at}-${index}`}>
                    <GameMark className="lobby-page__recent-round-mark" game={round.game_id} />
                    <span className="lobby-page__recent-round-copy"><strong>{round.message}</strong><small><span>{round.game_name}</span><time dateTime={round.played_at}>{roundTime(round.played_at)}</time></small></span>
                    <span className={`lobby-page__recent-round-profit${round.profit > 0 ? ' lobby-page__recent-round-profit--positive' : round.profit < 0 ? ' lobby-page__recent-round-profit--negative' : ''}`} aria-label={`Итог: ${round.profit > 0 ? '+' : ''}${round.profit.toLocaleString('ru-RU')} фишек`}>
                      <small>Итог</small>
                      <strong>{round.profit > 0 ? '+' : ''}{round.profit.toLocaleString('ru-RU')}</strong>
                    </span>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <div className="lobby-page__empty lobby-page__empty--history">
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
