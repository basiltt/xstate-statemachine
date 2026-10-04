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
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ...exceptions import InvalidConfigError

__all__ = [
    "ActionObject",
    "ActionSpec",
    "InvokeConfig",
    "MachineConfig",
    "StateConfig",
    "TransitionConfig",
    "validate_machine_json",
]

_X_KEY = re.compile(r"^x-")
_BOM = chr(0xFEFF)  # a UTF-8 byte-order mark decoded into the str


class ActionObject(BaseModel):
    """`{type, params, ...}` -- `type` MUST be a string (#266 battle: the
    parser crashed with a bare ``AttributeError`` on ``{"type": 1}``)."""

    model_config = ConfigDict(extra="allow")

    type: str
    params: Optional[Dict[str, Any]] = None


#: An action: a name, a `{type, params}` object, or a list of either.
ActionSpec = Union[str, ActionObject]
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
    # 📝 #266 battle: a LIST target (XState v5 multi-target) is not
    #    implemented by the parser -- it crashed with AttributeError. The
    #    gate refuses it with a path instead of passing it through.
    target: Optional[str] = None
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
    # 📝 #266 battle (B): the parser refuses a context that is not an
    #    object (a str is tolerated as an unresolved Stately template
    #    placeholder, a callable as a factory); the gate accepted ANY value.
    context: Optional[Any] = None
    version: Optional[Union[str, int, float]] = None
    actionErrorPolicy: Optional[Literal["continue", "rollback", "fail"]] = None
    guardErrorPolicy: Optional[Literal["false", "true", "raise"]] = None
    onUnhandled: Optional[Literal["ignore", "defer", "error"]] = None
    maxIterations: Optional[int] = Field(default=None, ge=1)
    spawnBlockingTimeout: Optional[Union[int, float]] = Field(
        default=None, ge=0
    )
    # ⚠️ #266 battle (B): STRICT bools. The parser reads these with
    #    `bool(value)`, so `"false"` ENABLES strict mode; pydantic's lax
    #    coercion turned the same string into False -- the gate approved a
    #    chart meaning the opposite of what it said. Only JSON true/false.
    strict: Optional[bool] = Field(default=None, strict=True)
    strictTargets: Optional[bool] = Field(default=None, strict=True)
    strictConfig: Optional[bool] = Field(default=None, strict=True)

    @field_validator("context")
    @classmethod
    def _context_is_an_object(cls, v: Any) -> Any:
        if v is None or isinstance(v, (dict, str)) or callable(v):
            return v
        raise ValueError(f"context must be an object, got {type(v).__name__}")

    @model_validator(mode="after")
    def _root_has_states(self) -> "MachineConfig":
        if not self.states:
            raise ValueError("a machine must declare at least one state")
        return self

    @model_validator(mode="after")
    def _custom_ids_unique(self) -> "MachineConfig":
        # 📝 #266 battle (B): the parser refuses a duplicate custom state
        #    `id` (`#id` targets would be ambiguous); the gate passed it.
        seen: Dict[str, str] = {}

        def walk(node: StateConfig, path: str) -> None:
            for name, child in (node.states or {}).items():
                here = f"{path}.{name}" if path else f"states.{name}"
                if child.id is not None:
                    if child.id in seen:
                        raise ValueError(
                            f"duplicate state id {child.id!r} declared by "
                            f"{seen[child.id]} and {here}"
                        )
                    seen[child.id] = here
                walk(child, f"{here}.states")

        walk(self, "")
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


def _clean_loc(loc: Tuple[Any, ...]) -> str:
    """Drop pydantic's union-branch tags (``str``, ``list[union[...]]``,
    ``TransitionConfig``) so a location reads like the JSON path:
    ``states.a.on.X[0].target``. Integer segments are list indexes."""
    out = ""
    for p in loc:
        if isinstance(p, int):
            out += f"[{p}]"
        elif not _BRANCH_TAG.match(str(p)):
            out += f".{p}" if out else str(p)
    return out or "<root>"


def _format_errors(exc: ValidationError) -> str:
    # 📝 A value that fits none of a Union's branches produces one error
    #    PER branch. Collapse them to one line per JSON path, keeping the
    #    most specific message (the deepest location); then drop a path
    #    whose deeper child was also reported (#266 battle B: a bad
    #    `PAY[0].target` also printed "PAY: should be a valid string" and
    #    "PAY[0]: should be a valid string" -- the str branches' noise).
    best: Dict[str, Tuple[int, str]] = {}
    for e in exc.errors():
        loc = tuple(e.get("loc", ()))
        path = _clean_loc(loc)
        depth = len(loc)
        msg = str(e.get("msg"))
        if e.get("type") == "recursion_loop":
            # 📝 #266 battle (B): pydantic-core caps validator recursion at
            #    roughly 100 nested `states` and calls it a "cyclic
            #    reference" -- a JSON document cannot be cyclic. Say what
            #    happened. (The parser itself copes to a few hundred.)
            path = path.split(".states.")[0] + ".states..."
            msg = (
                "states nest deeper than the static gate supports "
                "(about 95 levels); create_machine() still parses it"
            )
        if path not in best or depth > best[path][0]:
            best[path] = (depth, msg)
    shown = [
        p
        for p in best
        if not any(q != p and q.startswith((p + ".", p + "[")) for q in best)
    ]
    return "\n".join(f"  {p}: {best[p][1]}" for p in shown)


def _no_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise InvalidConfigError(
                f"machine config JSON repeats the key {k!r} in one object; "
                f"only the last value would be used"
            )
        out[k] = v
    return out


def _load(raw: Union[str, bytes, bytearray, Dict[str, Any]]) -> Any:
    """Decode the JSON text forms; a dict passes through untouched.

    📝 #266 battle (B): ``bytes`` was refused as "got bytes", a UTF-8 BOM
    and malformed JSON escaped as a bare ``JSONDecodeError``, and a
    duplicated key silently kept the last value (a classic copy-paste bug
    that the gate is the only place able to see -- the engine receives an
    already-collapsed dict).
    """
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = bytes(raw).decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidConfigError(
                f"machine config is not UTF-8: {exc.reason}"
            ) from None
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(
            raw[1:] if raw.startswith(_BOM) else raw,
            object_pairs_hook=_no_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise InvalidConfigError(
            f"machine config is not valid JSON: {exc.msg} "
            f"(line {exc.lineno}, column {exc.colno})"
        ) from None


def validate_machine_json(
    raw: Union[str, bytes, bytearray, Dict[str, Any]], *, strict: bool = False
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

    ``raw`` may be a dict, JSON ``str``, or UTF-8 ``bytes`` (a BOM is
    tolerated). JSON text that repeats a key inside one object, or does
    not parse, is an `InvalidConfigError` too.
    """
    data = _load(raw)
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
