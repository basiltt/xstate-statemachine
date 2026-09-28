# src/xstate_statemachine/contrib/pydantic/config.py
"""`validate_machine_json()` -- a Pydantic model of the XState JSON subset
this library implements, with error PATHS, before `create_machine` (#266).

🏛️ Kept in lock-step with the parser by a test: the fields declared here
must equal `validation.KNOWN_ROOT_KEYS` / `KNOWN_STATE_KEYS` /
`KNOWN_TRANSITION_KEYS` / `KNOWN_INVOKE_KEYS` (plus the `x-` escape). If
`models.py` learns a key, this model fails its parity test until it learns
it too -- the same "silent acceptance is a bug" rule, applied to the
validator itself.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from ...exceptions import InvalidConfigError

__all__ = [
    "ActionSpec",
    "InvokeConfig",
    "MachineConfig",
    "StateConfig",
    "TransitionConfig",
    "validate_machine_json",
]

_X_KEY = re.compile(r"^x-")

#: An action: a name, a `{type, params}` object, or a list of either.
ActionSpec = Union[str, Dict[str, Any]]
Actions = Union[ActionSpec, List[ActionSpec]]
#: A guard: a name, `{type, params}`, or a composite `{and|or|not: ...}`.
GuardSpec = Union[str, Dict[str, Any]]


class _Loose(BaseModel):
    """Base: unknown keys are collected so the caller decides (`strict`)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def unknown_keys(self) -> List[str]:
        return sorted(
            k for k in (self.model_extra or {}) if not _X_KEY.match(k)
        )


class TransitionConfig(_Loose):
    target: Optional[Union[str, List[str]]] = None
    actions: Optional[Actions] = None
    guard: Optional[GuardSpec] = None
    cond: Optional[GuardSpec] = None  # XState v4 alias
    internal: Optional[bool] = None
    reenter: Optional[bool] = None
    meta: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tags: Optional[Union[str, List[str]]] = None


#: A transition: a bare target string, an object, or a list of objects
#: (guarded alternatives). `None` / `{}` is a targetless self-transition.
Transition = Union[
    str, TransitionConfig, List[Union[str, TransitionConfig]], None
]


class InvokeConfig(_Loose):
    src: Optional[str] = None
    id: Optional[str] = None
    input: Optional[Any] = None
    systemId: Optional[str] = None
    onDone: Transition = None
    onError: Transition = None
    meta: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tags: Optional[Union[str, List[str]]] = None


class StateConfig(_Loose):
    id: Optional[str] = None
    type: Optional[
        Literal["atomic", "compound", "parallel", "final", "history"]
    ] = None
    initial: Optional[str] = None
    states: Optional[Dict[str, "StateConfig"]] = None
    on: Optional[Dict[str, Transition]] = None
    entry: Optional[Actions] = None
    exit: Optional[Actions] = None
    after: Optional[Dict[Union[int, str], Transition]] = None
    always: Transition = None
    invoke: Optional[Union[InvokeConfig, List[InvokeConfig]]] = None
    onDone: Transition = None
    output: Optional[Any] = None
    history: Optional[Literal["shallow", "deep"]] = None
    target: Optional[str] = None  # history default
    meta: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tags: Optional[Union[str, List[str]]] = None

    @model_validator(mode="after")
    def _initial_names_a_child(self) -> "StateConfig":
        if self.initial is not None and self.states is not None:
            if self.initial not in self.states:
                raise ValueError(
                    f"initial state {self.initial!r} is not one of "
                    f"{sorted(self.states)}"
                )
        if (
            self.initial is not None
            and not self.states
            and self.type != "parallel"
            and not isinstance(
                self, MachineConfig
            )  # root: see _root_has_states
        ):
            raise ValueError(
                f"'initial' is {self.initial!r} but the state declares no "
                f"'states'"
            )
        return self


class MachineConfig(StateConfig):
    """The root: a state node plus context, version and the policies."""

    id: str = Field(min_length=1)
    context: Optional[Any] = None
    version: Optional[Union[str, int, float]] = None
    actionErrorPolicy: Optional[Literal["continue", "rollback", "fail"]] = None
    guardErrorPolicy: Optional[Literal["false", "true", "raise"]] = None
    onUnhandled: Optional[Literal["ignore", "defer", "error"]] = None
    maxIterations: Optional[int] = Field(default=None, ge=1)
    spawnBlockingTimeout: Optional[Union[int, float]] = Field(
        default=None, ge=0
    )
    strict: Optional[bool] = None
    strictTargets: Optional[bool] = None
    strictConfig: Optional[bool] = None

    @model_validator(mode="after")
    def _root_has_states(self) -> "MachineConfig":
        if not self.states:
            raise ValueError("a machine must declare at least one state")
        return self

    # -- helpers -----------------------------------------------------------------
    def all_state_ids(self) -> List[str]:
        """Every fully-qualified state id (``root.child.grandchild``)."""
        out: List[str] = []

        def walk(node: StateConfig, path: str) -> None:
            out.append(path)
            for name, child in (node.states or {}).items():
                walk(child, f"{path}.{name}")

        walk(self, self.id)
        return out

    def unknown_key_paths(self) -> List[str]:
        """``path.to.key`` for every unrecognised, non-``x-`` key."""
        found: List[str] = []

        def walk_t(t: Any, path: str) -> None:
            if isinstance(t, TransitionConfig):
                found.extend(f"{path}.{k}" for k in t.unknown_keys())
            elif isinstance(t, list):
                for i, item in enumerate(t):
                    walk_t(item, f"{path}[{i}]")

        def walk(node: StateConfig, path: str) -> None:
            found.extend(f"{path}.{k}" for k in node.unknown_keys())
            for ev, t in (node.on or {}).items():
                walk_t(t, f"{path}.on.{ev}")
            for d, t in (node.after or {}).items():
                walk_t(t, f"{path}.after.{d}")
            walk_t(node.always, f"{path}.always")
            walk_t(node.onDone, f"{path}.onDone")
            invokes = node.invoke
            if isinstance(invokes, InvokeConfig):
                invokes = [invokes]
            for i, inv in enumerate(invokes or []):
                found.extend(
                    f"{path}.invoke[{i}].{k}" for k in inv.unknown_keys()
                )
                walk_t(inv.onDone, f"{path}.invoke[{i}].onDone")
                walk_t(inv.onError, f"{path}.invoke[{i}].onError")
            for name, child in (node.states or {}).items():
                walk(child, f"{path}.states.{name}")

        walk(self, "")
        return [p.lstrip(".") for p in found]


_BRANCH_TAG = re.compile(
    r"^(str|int|float|bool|none|dict|list|union|literal|function-after|"
    r"tagged-union|nullable|TransitionConfig|InvokeConfig|StateConfig)"
    r"(\[.*\])?$"
)


def _clean_loc(loc: tuple) -> str:
    """Drop pydantic's union-branch tags (``str``, ``list[union[...]]``,
    ``TransitionConfig``) so a location reads like the JSON path:
    ``states.a.on.X.target``. Integer segments are list indexes and stay."""
    keep = [
        str(p)
        for p in loc
        if isinstance(p, int) or not _BRANCH_TAG.match(str(p))
    ]
    return ".".join(keep) or "<root>"


def _format_errors(exc: ValidationError) -> str:
    # 📝 A value that fits none of a Union's branches produces one error
    #    PER branch. Collapse them to one line per JSON path, keeping the
    #    most specific message (the deepest location).
    best: Dict[str, tuple] = {}
    for e in exc.errors():
        loc = tuple(e.get("loc", ()))
        path = _clean_loc(loc)
        depth = len(loc)
        if path not in best or depth > best[path][0]:
            best[path] = (depth, str(e.get("msg")))
    return "\n".join(f"  {path}: {msg}" for path, (_d, msg) in best.items())


def validate_machine_json(
    raw: Union[str, Dict[str, Any]], *, strict: bool = False
) -> MachineConfig:
    """Parse and validate an XState JSON config; raise `InvalidConfigError`
    with PATHS before `create_machine()` ever runs.

    Catches statically: a missing / empty ``id``, an ``initial`` that names
    no child, a wrong ``type`` / policy value, a non-integer ``maxIterations``,
    a transition target that is not a string, an ``invoke`` without a
    shape -- each reported as ``states.paying.on.PAY[0].target: <msg>``.
    With ``strict=True`` an unrecognised key anywhere (outside ``x-``) is
    an error too, mirroring ``strictConfig``.

    Unknown transition *targets* are the parser's job (they need the whole
    tree and the resolver); `create_machine` still reports those.
    """
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict):
        raise InvalidConfigError(
            f"machine config must be a JSON object, got {type(data).__name__}"
        )
    try:
        cfg = MachineConfig.model_validate(data)
    except ValidationError as exc:
        body = _format_errors(exc)
        raise InvalidConfigError(
            f"machine config is invalid ({body.count(chr(10)) + 1} "
            f"problem(s)):\n{body}"
        ) from exc
    if strict:
        unknown = cfg.unknown_key_paths()
        if unknown:
            raise InvalidConfigError(
                "machine config has unrecognised key(s) (strict): "
                + ", ".join(unknown)
            )
    return cfg
