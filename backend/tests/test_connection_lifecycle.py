import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest
from casino.persistence.sqlite import PlayerRepository
from casino.recovery import backup_database, validate_database


class TrackedConnection(sqlite3.Connection):
    closed = False

    def close(self) -> None:
        self.closed = True
        super().close()


def test_repository_backup_closes_connections_before_publish(tmp_path: Path) -> None:
    repository = PlayerRepository(tmp_path / "source.sqlite3")
    destination = tmp_path / "backup.sqlite3"
    connections: list[TrackedConnection] = []
    original_connect = sqlite3.connect

    def connect(*args, **kwargs) -> TrackedConnection:
        connection = original_connect(*args, **kwargs, factory=TrackedConnection)
        connections.append(connection)
        return connection

    from os import replace as original_replace

    def publish(source: Path, target: Path) -> None:
        assert connections and all(connection.closed for connection in connections)
        original_replace(source, target)

    with (
        patch("casino.persistence.sqlite.sqlite3.connect", side_effect=connect),
        patch("casino.persistence.sqlite.os.replace", side_effect=publish),
    ):
        repository.backup_to(destination)

    with closing(original_connect(destination)) as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert db.execute("SELECT balance FROM profile").fetchone()[0] == 2500


@pytest.mark.parametrize("operation", ["backup", "validate"])
def test_recovery_closes_source_when_destination_open_fails(tmp_path: Path, operation: str) -> None:
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    PlayerRepository(source)
    original_connect = sqlite3.connect
    connections: list[TrackedConnection] = []

    def connect(*args, **kwargs) -> TrackedConnection:
        if connections:
            raise sqlite3.OperationalError("injected destination open failure")
        connection = original_connect(*args, **kwargs, factory=TrackedConnection)
        connections.append(connection)
        return connection

    with (
        patch("casino.recovery.sqlite3.connect", side_effect=connect),
        pytest.raises(sqlite3.OperationalError, match="destination open failure"),
    ):
        if operation == "backup":
            backup_database(source, destination)
        else:
            validate_database(source)

    assert connections[0].closed
    assert not destination.exists()


def test_repository_closes_connection_when_configuration_fails(tmp_path: Path) -> None:
    repository = PlayerRepository(tmp_path / "source.sqlite3")

    class ConfigurationFaultConnection(TrackedConnection):
        def execute(self, sql, parameters=()):
            if "busy_timeout" in sql:
                raise sqlite3.OperationalError("injected PRAGMA failure")
            return super().execute(sql, parameters)

    connection = sqlite3.connect(repository.path, factory=ConfigurationFaultConnection)
    with (
        patch("casino.persistence.sqlite.sqlite3.connect", return_value=connection),
        pytest.raises(sqlite3.OperationalError, match="PRAGMA failure"),
    ):
        repository._connect()

    assert connection.closed
