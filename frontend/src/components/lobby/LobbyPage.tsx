import dealerPortrait from '../../assets/dealer-portrait.png'
import type { CasinoState, GameId } from '../../types'
import { Icon, type ShellIconName } from '../shell/Icon'
import type { RoomRoute } from '../shell/AppShell'

const gameDetails: Record<GameId, { description: string; icon: ShellIconName; tableNote: string }> = {
  blackjack: { description: 'Карты против дилера', icon: 'blackjack', tableNote: '3:2 · дилер стоит на 17' },
  slots: { description: 'Три барабана', icon: 'slots', tableNote: 'Тройка символов' },
  roulette: { description: 'Европейское колесо · 0–36', icon: 'roulette', tableNote: 'Красное · чёрное · зеро' },
}

const gameOrder: GameId[] = ['blackjack', 'roulette', 'slots']

function TableMark({ game }: { game: GameId }) {
  return (
    <svg className="table-entry-mark" viewBox="0 0 88 70" fill="none" aria-hidden="true" focusable="false">
      {game === 'blackjack' && <>
        <path d="M12 9h64v26c0 15-13 25-32 25S12 50 12 35V9Z" />
        <path d="M20 16h48v19c0 11-10 18-24 18S20 46 20 35V16Z" />
        <path d="M31 24c4-3 8-4 13-4s9 1 13 4" />
        <path d="M28 36h.1M60 36h.1" />
      </>}
      {game === 'roulette' && <>
        <circle cx="44" cy="35" r="27" />
        <circle cx="44" cy="35" r="20" />
        <circle cx="44" cy="35" r="6" />
        <path d="M44 8v7m0 40v7M17 35h7m40 0h7M25 16l5 5m28 28 5 5m0-38-5 5m-28 28-5 5M33 10l2 7m18 36 2 7M69 24l-7 3m-36 16-7 3m50 0-7-3m-36-16-7-3M55 10l-2 7m-18 36-2 7" />
      </>}
      {game === 'slots' && <>
        <path d="M13 12h62v46H13z" />
        <path d="M18 17h16v36H18zm18 0h16v36H36zm18 0h16v36H54z" />
        <path d="M24 26h4m14 0h4m14 0h4M24 44h4m14 0h4m14 0h4" />
      </>}
    </svg>
  )
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
      <section className="lobby-hero" aria-labelledby="lobby-title">
        <div className="lobby-hero-portrait" aria-hidden="true">
          <img src={dealerPortrait} alt="" />
        </div>
        <div className="lobby-hero-copy">
          <h1 id="lobby-title">Вечер<br />в NOIR.</h1>
          <p className="lobby-hero-description">Выбирай стол, делай ход, следи за игрой. В клубе — только виртуальные фишки.</p>
          <div className="lobby-hero-games" aria-label="Доступные игры">
            {orderedGames.map((game) => <span key={game.id}>{game.name}</span>)}
          </div>
          <a className="lobby-hero-cta" href="#table-registry">Выбрать стол <Icon name="arrow" /></a>
        </div>
        <div className="lobby-hero-host" aria-label="Ава, хозяйка клуба">
          <span>АВА</span><i />
        </div>
        <div className="lobby-hero-seal" aria-hidden="true">N</div>
      </section>

      <div className="lobby-layout">
        <section className="table-registry" id="table-registry" aria-labelledby="table-registry-title">
          <div className="lobby-section-heading">
            <h2 id="table-registry-title">Столы клуба</h2>
            <span>{games.length} {games.length % 10 === 1 && games.length % 100 !== 11 ? 'игра' : games.length % 10 >= 2 && games.length % 10 <= 4 && (games.length % 100 < 12 || games.length % 100 > 14) ? 'игры' : 'игр'}</span>
          </div>
          {orderedGames.length ? (
            <div className="table-list">
              {orderedGames.map((game) => {
                const details = gameDetails[game.id]
                return details ? (
                  <button className="table-entry" data-game={game.id} key={game.id} type="button" onClick={() => onOpen(game.id)}>
                    <span className="table-entry-symbol"><TableMark game={game.id} /></span>
                    <span className="table-entry-main">
                      <strong>{game.name}</strong>
                      <span>{details.description}</span>
                      <small>{details.tableNote}</small>
                    </span>
                    <span className="table-limits">
                      <small>{game.maximum_bet === undefined ? 'МИН. СТАВКА' : 'СТАВКА'}</small>
                      <strong>{game.maximum_bet === undefined ? `от ${game.minimum_bet.toLocaleString('ru-RU')}` : `${game.minimum_bet.toLocaleString('ru-RU')}–${game.maximum_bet.toLocaleString('ru-RU')}`}</strong>
                      {game.maximum_bet === undefined && <em>верхний лимит не передан API</em>}
                    </span>
                    <span className="table-entry-action">Войти<Icon name="arrow" /></span>
                  </button>
                ) : null
              })}
            </div>
          ) : (
            <div className="lobby-empty lobby-empty--tables" role="status">
              <strong>Список столов не получен</strong>
              <span>Обновите состояние сервера, чтобы загрузить доступные игры.</span>
              <button type="button" onClick={onRetry}>Обновить список</button>
            </div>
          )}
          <p className="table-registry-note">Ставки и результаты обрабатываются локально. Только демо-фишки.</p>
        </section>

        <aside className="lobby-side-column">
          <section className="player-ledger" aria-label="Ваш игровой счёт">
            <div className="ledger-balance">
              <span>ДЕМО-БАЛАНС</span>
              <strong>{player.balance.toLocaleString('ru-RU')}</strong>
              <small>виртуальных фишек</small>
            </div>
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
              <ol className="recent-round-list">
                {latestRounds.map((round, index) => (
                  <li key={`${round.played_at}-${index}`}>
                    <span className="recent-round-icon"><Icon name={gameDetails[round.game_id].icon} /></span>
                    <span className="recent-round-copy"><strong>{round.game_name}</strong><small>{round.message}</small></span>
                    <span className={`recent-round-profit${round.profit > 0 ? ' is-positive' : round.profit < 0 ? ' is-negative' : ''}`}>
                      {round.profit > 0 ? '+' : ''}{round.profit.toLocaleString('ru-RU')}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="lobby-empty lobby-empty--history">
                <span>История пока пуста</span>
                <p>Завершённые раунды появятся здесь.</p>
                <button type="button" onClick={() => onOpen('blackjack')}>Открыть блэкджек<Icon name="arrow" /></button>
              </div>
            )}
          </section>
        </aside>
      </div>
    </div>
  )
}
