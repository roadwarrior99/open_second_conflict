"""Pseudo-RNG wrapper matching FUN_1000_1f75 behaviour.

The original game calls FUN_1000_1f75(N) to get a random integer in [0, N-1].
We wrap Python's random module so the seed can be controlled for replay fidelity.
"""
import random as _random


class GameRNG:
    def __init__(self, seed=None):
        self._rng = _random.Random(seed)

    def rand(self, n: int) -> int:
        """Return a random integer in [0, n-1], matching FUN_1000_1f75(n)."""
        if n <= 0:
            return 0
        return self._rng.randint(0, n - 1)

    def seed(self, s):
        self._rng.seed(s)


# Module-level default instance used by engine modules
_default = GameRNG()


def rand(n: int) -> int:
    return _default.rand(n)


def seed(s):
    _default.seed(s)