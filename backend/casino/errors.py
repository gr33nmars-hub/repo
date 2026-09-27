class IdempotencyConflict(ValueError):
    """A request key exists but cannot safely identify this operation."""


class StaleGameState(ValueError):
    """The client made a game action against a state that has since changed."""
