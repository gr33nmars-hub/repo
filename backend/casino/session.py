"""Compatibility facade for the casino application service."""

from casino.application.service import CasinoService
from casino.persistence.sqlite import PlayerRepository


class CasinoSession(CasinoService):
    """Preserve the former convenience constructor during the architecture migration."""

    def __init__(self, repository: PlayerRepository | None = None) -> None:
        super().__init__(repository or PlayerRepository())
