# src/xstate_statemachine/patterns/retry.py
# -----------------------------------------------------------------------------
# 🔁 RetryPolicy -- exponential backoff with jitter, as machine logic (#265)
# -----------------------------------------------------------------------------
# 🏛️ Why a policy object and not a loop: in a statechart the retry IS the
#    chart -- `attempting --error--> retrying --after(delay)--> attempting`
#    -- so the only thing a library can usefully add is the DELAY function
#    and the three trivial pieces of logic around it (can we retry? bump
#    the counter; reset it). `RetryPolicy.logic()` hands those to
#    `MachineLogic` under predictable names, so the JSON fragment in the
#    docs works verbatim and `xsm inspect` renders the retry loop.
#
# 📝 Jitter formulas follow the AWS Architecture Blog ("Exponential Backoff
#    And Jitter", Brooker 2015). `decorrelated` is deliberately NON-monotone
#    in the attempt number -- each delay depends on the previous one -- so
#    its only guarantees are the bounds. `rng` is injectable so tests are
#    deterministic (X0: no hidden global state).
# -----------------------------------------------------------------------------
"""`RetryPolicy`: backoff + jitter delays and the retry-loop logic."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Literal, Optional

from ..machine_logic import MachineLogic

__all__ = ["RetryPolicy", "JitterMode"]

JitterMode = Literal["none", "full", "equal", "decorrelated"]
_MODES = ("none", "full", "equal", "decorrelated")


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with jitter, plus the machine logic to drive it.

    Attributes:
        max_attempts: Total attempts allowed, INCLUDING the first. With
            ``max_attempts=3`` the machine tries, retries twice, and the
            third failure is final (``guard_can_retry`` returns False).
        base_ms: Delay before the first retry (attempt 1 → attempt 2).
        factor: Exponential growth per attempt.
        max_ms: Upper bound on any delay (the "cap").
        jitter: ``"none"`` (pure exponential), ``"full"`` (uniform in
            ``[0, exp]``), ``"equal"`` (``exp/2 + uniform[0, exp/2]``) or
            ``"decorrelated"`` (``min(cap, uniform[base, prev*3])``).
        rng: A ``() -> float in [0, 1)``; defaults to ``random.random``.
            Inject a seeded one for deterministic tests.

    ``delay_ms(attempt)`` takes the 1-based number of the attempt that just
    FAILED and returns how long to wait before the next one.
    """

    max_attempts: int = 5
    base_ms: float = 200.0
    factor: float = 2.0
    max_ms: float = 30_000.0
    jitter: JitterMode = "full"
    rng: Callable[[], float] = field(default=random.random, repr=False)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_ms < 0 or self.max_ms < 0:
            raise ValueError("base_ms and max_ms must be >= 0")
        if self.factor < 1.0:
            raise ValueError("factor must be >= 1.0")
        if self.jitter not in _MODES:
            raise ValueError(f"jitter must be one of {_MODES}")

    # -- delay computation ------------------------------------------------
    def exponential_ms(self, attempt: int) -> float:
        """The un-jittered, capped delay after *attempt* (1-based)."""
        if attempt < 1:
            raise ValueError("attempt is 1-based")
        return min(self.max_ms, self.base_ms * (self.factor ** (attempt - 1)))

    def delay_ms(
        self, attempt: int, *, previous_ms: Optional[float] = None
    ) -> float:
        """Delay before the next try, after *attempt* failed.

        Args:
            attempt: 1-based number of the attempt that failed.
            previous_ms: For ``"decorrelated"`` only -- the previous delay
                (``None`` → ``base_ms``). Other modes ignore it.
        """
        exp = self.exponential_ms(attempt)
        if self.jitter == "none":
            return exp
        if self.jitter == "full":
            return self.rng() * exp
        if self.jitter == "equal":
            half = exp / 2.0
            return half + self.rng() * half
        # decorrelated: sleep = min(cap, random_between(base, sleep * 3))
        prev = self.base_ms if previous_ms is None else previous_ms
        lo, hi = self.base_ms, max(self.base_ms, prev * 3.0)
        return min(self.max_ms, lo + self.rng() * (hi - lo))

    # -- machine logic ----------------------------------------------------
    def as_delay(
        self, attempt_key: str = "attempt"
    ) -> Callable[[Dict[str, Any], Any], float]:
        """A named-delay implementation reading ``ctx[attempt_key]``.

        The counter is the number of attempts made so far (bumped by
        ``action_bump`` on each failure), so ``ctx[attempt_key] == 1``
        means "the first attempt failed" and yields ``delay_ms(1)``. For
        ``"decorrelated"`` the previous delay is remembered under
        ``ctx[f"{attempt_key}_delay_ms"]``.
        """
        prev_key = f"{attempt_key}_delay_ms"

        def _delay(context: Dict[str, Any], event: Any) -> float:
            attempt = max(1, int(context.get(attempt_key, 1)))
            prev = (
                context.get(prev_key)
                if self.jitter == "decorrelated"
                else None
            )
            ms = self.delay_ms(attempt, previous_ms=prev)
            if self.jitter == "decorrelated":
                context[prev_key] = ms
            return ms

        _delay.__name__ = f"retry_delay_{attempt_key}"
        return _delay

    def guard_can_retry(
        self, attempt_key: str = "attempt"
    ) -> Callable[[Dict[str, Any], Any], bool]:
        """Guard: ``ctx[attempt_key] < max_attempts`` (another try is allowed)."""

        def _can_retry(context: Dict[str, Any], event: Any) -> bool:
            return int(context.get(attempt_key, 0)) < self.max_attempts

        _can_retry.__name__ = f"retry_can_retry_{attempt_key}"
        return _can_retry

    def action_bump(self, attempt_key: str = "attempt") -> Callable[..., None]:
        """Action: ``ctx[attempt_key] += 1`` -- call it on each failure."""

        def _bump(i: Any, context: Dict[str, Any], e: Any, a: Any) -> None:
            context[attempt_key] = int(context.get(attempt_key, 0)) + 1

        _bump.__name__ = f"retry_bump_{attempt_key}"
        return _bump

    def action_reset(
        self, attempt_key: str = "attempt"
    ) -> Callable[..., None]:
        """Action: ``ctx[attempt_key] = 0`` (and forget the decorrelated
        previous delay) -- call it on success."""
        prev_key = f"{attempt_key}_delay_ms"

        def _reset(i: Any, context: Dict[str, Any], e: Any, a: Any) -> None:
            context[attempt_key] = 0
            context.pop(prev_key, None)

        _reset.__name__ = f"retry_reset_{attempt_key}"
        return _reset

    def logic(
        self, prefix: str = "retry", attempt_key: str = "attempt"
    ) -> MachineLogic:
        """A `MachineLogic` with ``{prefix}Delay`` (named delay),
        ``{prefix}CanRetry`` (guard), ``{prefix}Bump`` / ``{prefix}Reset``
        (actions). Merge it into your own with `MachineLogic.merge` or
        pass it directly when the chart has no other logic.

        JSON fragment it drives::

            "attempting": {
              "invoke": {"src": "work",
                         "onDone":  {"target": "done", "actions": "retryReset"},
                         "onError": {"target": "retrying", "actions": "retryBump"}}},
            "retrying": {
              "after": {"retryDelay": [
                {"guard": "retryCanRetry", "target": "attempting"},
                {"target": "deadLettered"}]}},
        """
        return MachineLogic(
            actions={
                f"{prefix}Bump": self.action_bump(attempt_key),
                f"{prefix}Reset": self.action_reset(attempt_key),
            },
            guards={f"{prefix}CanRetry": self.guard_can_retry(attempt_key)},
            delays={f"{prefix}Delay": self.as_delay(attempt_key)},
        )
