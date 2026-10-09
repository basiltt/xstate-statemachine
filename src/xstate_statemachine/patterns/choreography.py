# src/xstate_statemachine/patterns/choreography.py
# -----------------------------------------------------------------------------
# 💃 ChoreographyRouter -- machines reacting to each other over a bus (#295)
# -----------------------------------------------------------------------------
# 🏛️ The other half of sagas: no orchestrator, each machine subscribes to
#    the integration events it cares about and publishes its own. This is
#    `InboundDispatcher` (#293) plus two rules, nothing more:
#
#      * ROUTING -- ``type → (machine, EVENT)``: an integration event
#        (``order.placed``) becomes a machine event (``PLACE``) on the
#        instance keyed by the envelope's ``subject`` (the business key).
#        Instances are stored under ``<machine id>:<subject>`` so an Order
#        and a Payment can share one business key.
#      * CAUSATION -- `OutboxPlugin` stamps every published envelope with
#        ``causationid`` = the envelope that caused it and inherits its
#        ``correlationid``, so the whole conversation is one chain.
#
#    Use `ChoreographyRouter.run_until_quiet()` in tests: it pumps the bus
#    until no topic has pending traffic.
# -----------------------------------------------------------------------------
"""`ChoreographyRouter`, `Route`."""

from __future__ import annotations

from typing import Any, Dict, Iterable, NamedTuple, Optional, Tuple, Union

from ..eda.dispatcher import DispatchResult, InboundDispatcher
from ..eda.envelope import Envelope, default_event_name

__all__ = ["ChoreographyRouter", "Route"]

#: Upper bound on bus rounds `run_until_quiet` performs (loop guard).
MAX_ROUNDS = 1000


class Route(NamedTuple):
    """Deliver envelopes of one type to *machine* as event *event*."""

    machine: Any
    event: Optional[str] = None


RouteSpec = Union[Any, Tuple[Any, str], Route]


class ChoreographyRouter:
    """An `InboundDispatcher` over a ``type → machine`` mapping.

    Args:
        store: `StateStore` for every participating machine.
        routes: ``{envelope_type: machine | (machine, EVENT) | Route}``.
            Without an explicit EVENT the default applies
            (``xsm.<machine>.<EVENT>`` → ``EVENT``, else the type itself).
        topics: Topics the router consumes (default ``("events",)``).
        **dispatcher_kw: Passed to `InboundDispatcher` (``plugins`` with
            an `OutboxPlugin`, ``inbox``, ``lock``, ``clock``, ...).
    """

    def __init__(
        self,
        store: Any,
        routes: Dict[str, RouteSpec],
        *,
        topics: Iterable[str] = ("events",),
        **dispatcher_kw: Any,
    ) -> None:
        self.routes: Dict[str, Route] = {
            t: self._route(spec) for t, spec in routes.items()
        }
        self.topics = tuple(topics)
        dispatcher_kw.setdefault("key_for", self.instance_key)
        # 📝 A shared bus carries events for OTHER services: not poison.
        dispatcher_kw.setdefault("on_unknown", "ignore")
        self.dispatcher = InboundDispatcher(
            store,
            self.machine_for,
            event_type=self.event_for,
            **dispatcher_kw,
        )

    @staticmethod
    def _route(spec: RouteSpec) -> Route:
        if isinstance(spec, Route):
            return spec
        if isinstance(spec, tuple):
            return Route(spec[0], spec[1])
        return Route(spec, None)

    # -- routing --------------------------------------------------------------
    def machine_for(self, envelope_type: str) -> Any:
        """The machine routed for *envelope_type*, or ``None`` (acked)."""
        route = self.routes.get(envelope_type)
        return route.machine if route else None

    def event_for(self, envelope: Envelope) -> str:
        """The machine event an envelope becomes (route EVENT or default)."""
        route = self.routes.get(envelope.type)
        if route is not None and route.event:
            return route.event
        return default_event_name(envelope.type)

    @staticmethod
    def instance_key(envelope: Envelope, machine: Any) -> str:
        """Store key ``<machine id>:<subject>`` (one key, many machines)."""
        return f"{machine.id}:{envelope.subject}"

    # -- running --------------------------------------------------------------
    async def run_once(self, broker: Any) -> DispatchResult:
        """One dispatcher pass over every topic; the merged result."""
        total = DispatchResult()
        for topic in self.topics:
            total.add(await self.dispatcher.run_once(broker, topic))
        return total

    async def run_until_quiet(
        self, broker: Any, *, max_rounds: int = MAX_ROUNDS
    ) -> DispatchResult:
        """Pump every topic until one round handles nothing.

        Args:
            broker: The bus (`FakeBrokerAdapter` in tests).
            max_rounds: Loop guard; must be >= 1.

        Returns:
            Every round's outcomes merged.

        Raises:
            ValueError: *max_rounds* < 1.
            RuntimeError: traffic was still flowing after *max_rounds* --
                usually two machines publishing at each other forever.
        """
        _check_rounds(max_rounds)
        total = DispatchResult()
        for _ in range(max_rounds):
            res = await self.run_once(broker)
            total.add(res)
            if not res.outcomes:
                return total
        raise _unsettled(max_rounds)

    def run_until_quiet_sync(
        self, broker: Any, *, max_rounds: int = MAX_ROUNDS
    ) -> DispatchResult:
        """Blocking twin of `run_until_quiet` (a `SyncBrokerAdapter`)."""
        _check_rounds(max_rounds)
        total = DispatchResult()
        for _ in range(max_rounds):
            res = DispatchResult()
            for topic in self.topics:
                res.add(self.dispatcher.run_once_sync(broker, topic))
            total.add(res)
            if not res.outcomes:
                return total
        raise _unsettled(max_rounds)


def _check_rounds(max_rounds: int) -> None:
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int):
        raise ValueError(f"max_rounds must be an int, got {max_rounds!r}")
    if max_rounds < 1:
        raise ValueError(f"max_rounds must be >= 1, got {max_rounds}")


def _unsettled(max_rounds: int) -> RuntimeError:
    # 📝 Same text from both engines so one runbook line matches either.
    return RuntimeError(
        f"choreography did not settle in {max_rounds} rounds "
        f"(an event loop between machines?)"
    )
