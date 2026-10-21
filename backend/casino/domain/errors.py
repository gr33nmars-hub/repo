"""Failures raised when a game or domain rule rejects an operation."""


class InvalidCasinoCommand(ValueError):
    """A well-formed request violates an available game or wallet rule."""
