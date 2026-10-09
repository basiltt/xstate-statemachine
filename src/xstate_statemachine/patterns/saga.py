# src/xstate_statemachine/patterns/saga.py
# -----------------------------------------------------------------------------
# 🧾 SagaBuilder -- orchestrated sagas as PLAIN statechart JSON (#295)
# -----------------------------------------------------------------------------
# 🏛️ Every saga tutorial hand-builds the same machine: a step ledger, a
#    per-step timeout, compensation in reverse order, retries. Those are
#    exactly `invoke` + `after` + `onError` + context. The builder emits the
#    JSON a human would have written -- no runtime magic, Stately-editable,
#    `strictConfig`-clean -- plus `logic()`, the handful of generic actions
#    it references. Your services stay yours.
#
#    Shape for steps a, b, c (each `steps.<name>` invokes its service):
#
#      steps.a --done--> steps.b --done--> steps.c --done--> completed
#         |error/timeout   |error/timeout    |error/timeout
#         v                v                 v
#       failed        compensating.a    compensating.b → compensating.a
#                          |                                  |
#                          +------------> failed <------------+
#
#    * a step with ``retry=RetryPolicy(...)`` fails into
#      ``steps.<name>Retrying``, which waits the policy's delay and re-enters
#      the step while ``<step>RetryCanRetry`` holds, else compensates;
#    * only steps that declared ``compensate`` get a compensating state;
#      compensation walks the COMPLETED steps in reverse, each exactly once
#      (entering a state once runs its invoke once);
#    * a compensation that itself fails ends in ``compensationFailed``,
#      tagged ``dead-letter`` so `DeadLetterPlugin` captures it;
#    * every step transition carries ``meta.publish`` (#293) -- with an
#      `OutboxPlugin` the saga emits ``<saga>.<step>.completed`` /
#      ``.failed`` / ``.compensated`` integration events.
# -----------------------------------------------------------------------------
"""`SagaBuilder`, `SagaStep`."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..machine_logic import MachineLogic
from .retry import RetryPolicy

__all__ = ["SagaBuilder", "SagaStep"]

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
#: Prefixes of events only the engine mints; a start event named like one
#: could never be sent by a caller (#79/#195 provenance checks).
_ENGINE_PREFIXES = ("done.", "error.", "xstate.", "after.")


def _check_key(what: str, key: Any) -> None:
    """Refuse an empty / non-string service or action key at declaration."""
    if not isinstance(key, str) or not key.strip():
        raise ValueError(f"{what} must be a non-empty string, got {key!r}")


def _check_event(event: Any) -> None:
    """Refuse a start event a caller could never deliver."""
    _check_key("start_event", event)
    if event.startswith(_ENGINE_PREFIXES):
        raise ValueError(
            f"start_event {event!r} is an engine-reserved event name"
        )


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


@dataclass(frozen=True)
class SagaStep:
    """One step: invoke *invoke*; undo with *compensate* on a later failure."""

    name: str
    invoke: str
    compensate: Optional[str] = None
    timeout_ms: Optional[int] = None
    retry: Optional[RetryPolicy] = None

    @property
    def retry_prefix(self) -> str:
        return f"{_camel(self.name)}Retry"

    @property
    def attempt_key(self) -> str:
        return f"attempt_{self.name}"


class SagaBuilder:
    """Fluent builder for an orchestrated saga chart.

    ::

        saga = (SagaBuilder("order_fulfilment")
            .step("reserve_stock", invoke="reserveStock",
                  compensate="releaseStock", timeout_ms=5000,
                  retry=RetryPolicy(max_attempts=3))
            .step("charge_card", invoke="chargeCard", compensate="refundCard")
            .step("ship", invoke="ship")
            .on_failure("notifyOps"))
        config = saga.build()                    # plain JSON dict
        machine = create_machine(config, logic=saga.logic().merge(mine))

    Args:
        name: The machine id (also the event-type prefix).
        start_event: When set, the saga waits in ``idle`` for this event
            (the shape an `InboundDispatcher` drives) and keeps its payload
            in ``context.input`` for the services; by default it starts
            the first step as soon as the interpreter starts.
    """

    def __init__(self, name: str, *, start_event: Optional[str] = None):
        if not isinstance(name, str) or not _NAME.match(name):
            raise ValueError(f"saga name {name!r} must be an identifier")
        if start_event is not None:
            _check_event(start_event)
        self.name = name
        self.start_event = start_event
        self._steps: List[SagaStep] = []
        self._on_failure: List[str] = []

    # -- declaration ------------------------------------------------------------
    def step(
        self,
        name: str,
        *,
        invoke: str,
        compensate: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        retry: Optional[RetryPolicy] = None,
    ) -> "SagaBuilder":
        """Append a step (steps run in declaration order).

        Args:
            name: Step identifier; also the ``invoke`` id and the middle of
                its event types (``<saga>.<name>.completed``).
            invoke: Service key that performs the step. Its return value
                lands in ``context.results[name]``; raising fails the step.
            compensate: Service key that undoes the step after a LATER
                step fails. Must be idempotent: a restart mid-compensation
                runs it again.
            timeout_ms: Fail the step after this many milliseconds (a
                positive ``int``).
            retry: Re-run a failed or timed-out step per this policy
                before compensating.

        Returns:
            The builder (fluent).

        Raises:
            ValueError: a non-identifier or duplicate name, a name that
                collides with a generated ``<step>Retrying`` state, an
                empty service key, a non-positive or non-integer
                ``timeout_ms``, or a *retry* that is not a `RetryPolicy`.
        """
        self._check_step_name(name)
        if retry is not None and f"{name}Retrying" in {
            s.name for s in self._steps
        }:
            raise ValueError(
                f"step {name!r} with retry= collides with step "
                f"'{name}Retrying' (its generated waiting state)"
            )
        _check_key("invoke", invoke)
        if compensate is not None:
            _check_key("compensate", compensate)
        if timeout_ms is not None and (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or timeout_ms <= 0
        ):
            raise ValueError(
                f"timeout_ms must be a positive int, got {timeout_ms!r}"
            )
        if retry is not None and not isinstance(retry, RetryPolicy):
            raise ValueError(
                f"retry must be a RetryPolicy, got {type(retry).__name__}"
            )
        self._steps.append(
            SagaStep(name, invoke, compensate, timeout_ms, retry)
        )
        return self

    def _check_step_name(self, name: str) -> None:
        if not isinstance(name, str) or not _NAME.match(name):
            raise ValueError(f"step name {name!r} must be an identifier")
        taken = {s.name for s in self._steps}
        taken |= {f"{s.name}Retrying" for s in self._steps if s.retry}
        if name in taken:
            raise ValueError(f"duplicate step {name!r}")

    def on_failure(self, *actions: str) -> "SagaBuilder":
        """Actions run on entering ``failed`` (after compensation).

        Raises:
            ValueError: an action name that is not a non-empty string.
        """
        for a in actions:
            _check_key("on_failure action", a)
        self._on_failure.extend(actions)
        return self

    @property
    def steps(self) -> List[SagaStep]:
        """The declared steps, in order (a copy)."""
        return list(self._steps)

    # -- JSON ---------------------------------------------------------------------
    def build(self) -> Dict[str, Any]:
        """The saga as a plain XState JSON config (a new dict each call)."""
        if not self._steps:
            raise ValueError("a saga needs at least one step")
        ctx: Dict[str, Any] = {
            "results": {},
            "compensated": [],
            "error": None,
        }
        for s in self._steps:
            if s.retry is not None:
                ctx[s.attempt_key] = 0
        states: Dict[str, Any] = {}
        if self.start_event:
            # 🐛 #295-a: the start event's payload was silently dropped
            #    (services could not see START's data); `sagaStart` keeps
            #    it in ``context.input``.
            ctx["input"] = None
            states["idle"] = {
                "on": {
                    self.start_event: {
                        "target": "steps",
                        "actions": ["sagaStart"],
                    }
                }
            }
        states["steps"] = {
            "initial": self._steps[0].name,
            "states": self._step_states(),
        }
        comp = self._compensation_states()
        if comp:
            states["compensating"] = {
                "initial": next(iter(comp)),
                "states": comp,
            }
        states["completed"] = {"type": "final", "tags": ["publish"]}
        failed: Dict[str, Any] = {"type": "final", "tags": ["publish"]}
        if self._on_failure:
            failed["entry"] = list(self._on_failure)
        states["failed"] = failed
        states["compensationFailed"] = {
            "type": "final",
            "tags": ["dead-letter", "publish"],
        }
        return {
            "id": self.name,
            "initial": "idle" if self.start_event else "steps",
            "context": ctx,
            "states": states,
        }

    def _ref(self, path: str) -> str:
        return f"#{self.name}.{path}"

    def _publish(self, step: str, what: str) -> Dict[str, Any]:
        return {"publish": {"type": f"{self.name}.{step}.{what}"}}

    def _failure_target(self, k: int) -> str:
        """Where a failure of step *k* goes: the latest compensable
        completed step's compensation, else ``failed``."""
        for j in range(k - 1, -1, -1):
            if self._steps[j].compensate:
                return self._ref(f"compensating.{self._steps[j].name}")
        return self._ref("failed")

    def _step_states(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        n = len(self._steps)
        for k, s in enumerate(self._steps):
            nxt = (
                self._ref(f"steps.{self._steps[k + 1].name}")
                if k + 1 < n
                else self._ref("completed")
            )
            ok_actions: List[Any] = [
                {"type": "sagaRecord", "params": {"step": s.name}}
            ]
            if s.retry is not None:
                ok_actions.append(f"{s.retry_prefix}Reset")
            fail_target = (
                self._ref(f"steps.{s.name}Retrying")
                if s.retry is not None
                else self._failure_target(k)
            )

            def failing(reason: str, _s: SagaStep = s) -> Dict[str, Any]:
                acts: List[Any] = [
                    {
                        "type": "sagaFail",
                        "params": {"step": _s.name, "reason": reason},
                    }
                ]
                if _s.retry is not None:
                    acts.insert(0, f"{_s.retry_prefix}Bump")
                return {
                    "target": fail_target,
                    "actions": acts,
                    "meta": self._publish(_s.name, "failed"),
                }

            node: Dict[str, Any] = {
                "invoke": {
                    "id": s.name,
                    "src": s.invoke,
                    "onDone": {
                        "target": nxt,
                        "actions": ok_actions,
                        "meta": self._publish(s.name, "completed"),
                    },
                    "onError": failing("error"),
                }
            }
            if s.timeout_ms is not None:
                node["after"] = {str(s.timeout_ms): failing("timeout")}
            out[s.name] = node
            if s.retry is not None:
                out[f"{s.name}Retrying"] = {
                    "after": {
                        f"{s.retry_prefix}Delay": [
                            {
                                "guard": f"{s.retry_prefix}CanRetry",
                                "target": s.name,
                            },
                            {"target": self._failure_target(k)},
                        ]
                    }
                }
        return out

    def _compensation_states(self) -> Dict[str, Any]:
        """Latest compensable step first (the entry order of a rollback)."""
        comp = [(k, s) for k, s in enumerate(self._steps) if s.compensate]
        out: Dict[str, Any] = {}
        for idx in range(len(comp) - 1, -1, -1):
            k, s = comp[idx]
            nxt = (
                self._ref(f"compensating.{comp[idx - 1][1].name}")
                if idx > 0
                else self._ref("failed")
            )
            out[s.name] = {
                "invoke": {
                    "id": f"compensate_{s.name}",
                    "src": s.compensate,
                    "onDone": {
                        "target": nxt,
                        "actions": [
                            {
                                "type": "sagaCompensated",
                                "params": {"step": s.name},
                            }
                        ],
                        "meta": self._publish(s.name, "compensated"),
                    },
                    "onError": {
                        "target": self._ref("compensationFailed"),
                        "actions": [
                            {
                                "type": "sagaFail",
                                "params": {
                                    "step": s.name,
                                    "reason": "compensation",
                                },
                            }
                        ],
                    },
                }
            }
        return out

    # -- logic ----------------------------------------------------------------------
    def logic(self) -> MachineLogic:
        """The generic actions (and per-step retry logic) the JSON names.

        Merge your services into it: ``saga.logic().merge(MachineLogic(
        services={...}))``.
        """
        merged: MachineLogic[Any] = MachineLogic(
            actions={
                "sagaStart": _start,
                "sagaRecord": _record,
                "sagaFail": _fail,
                "sagaCompensated": _compensated,
            }
        )
        for s in self._steps:
            if s.retry is not None:
                merged = merged.merge(
                    s.retry.logic(s.retry_prefix, s.attempt_key)
                )
        return merged


def _params(a: Any) -> Dict[str, Any]:
    p = getattr(a, "params", None)
    return p if isinstance(p, dict) else {}


def _start(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    payload = getattr(e, "payload", None)
    ctx["input"] = dict(payload) if isinstance(payload, dict) else None


def _record(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx.setdefault("results", {})[_params(a).get("step")] = getattr(
        e, "data", None
    )


def _fail(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    p = _params(a)
    err = getattr(e, "error", None) or getattr(e, "data", None)
    ctx["error"] = {
        "step": p.get("step"),
        "reason": p.get("reason"),
        "type": type(err).__name__ if isinstance(err, BaseException) else None,
        "message": str(err) if isinstance(err, BaseException) else None,
    }


def _compensated(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx.setdefault("compensated", []).append(_params(a).get("step"))
