"""Фасад обратной совместимости для сервиса приложения."""

from casino.application.service import CasinoService
from casino.persistence.sqlite import PlayerRepository


class CasinoSession(CasinoService):
    """Обёртка сервиса казино с созданием репозитория по умолчанию."""

    def __init__(self, repository: PlayerRepository | None = None) -> None:
        super().__init__(repository or PlayerRepository())
