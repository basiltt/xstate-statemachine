# tests/recipes/test_form_wizard.py
"""Wizard recipe: the core, then both front ends imported against stub
`streamlit` / `gradio` modules -- neither library is a dependency."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any, Dict, List

import pytest

from .conftest import load_recipe

wz = load_recipe("form_wizard", "wizard")


class TestCore:
    def test_forward_back_and_guards(self) -> None:
        session: Dict[str, Any] = {}
        w = wz.Wizard(session)
        assert w.step == "account"
        assert w.send("NEXT", email="nope") is False  # guard refuses
        assert w.send("NEXT", email="a@b.c") and w.step == "plan"
        assert w.send("BACK") and w.step == "account"
        assert w.data["email"] == "a@b.c"  # kept across BACK
        w.send("NEXT", email="a@b.c")
        assert w.send("NEXT", plan="gold") is False
        w.send("NEXT", plan="pro")
        assert w.send("SUBMIT", accepted=False) is False
        assert w.send("SUBMIT", accepted=True) and w.step == "done"
        assert w.data == {"email": "a@b.c", "plan": "pro", "accepted": True}

    def test_state_is_only_a_json_snapshot(self) -> None:
        session: Dict[str, Any] = {}
        wz.Wizard(session).send("NEXT", email="a@b.c")
        assert isinstance(session[wz.KEY], str)
        assert wz.Wizard(dict(session)).step == "plan"  # a copy restores

    def test_diagram_matches_the_chart(self) -> None:
        mm = wz.diagram()
        assert mm.startswith("stateDiagram-v2")
        assert "confirm --> done : SUBMIT" in mm


# -- Streamlit ----------------------------------------------------------------
class StubStreamlit(types.ModuleType):
    def __init__(self, clicks: List[str], **inputs: Any) -> None:
        super().__init__("streamlit")
        self.session_state: Dict[str, Any] = {}
        self.clicks, self.inputs, self.out = clicks, inputs, []

    def header(self, s: str) -> None:
        self.out.append(("header", s))

    def text_input(self, label: str, value: str = "") -> str:
        return self.inputs.get("email", value)

    def radio(self, label: str, options: Any) -> str:
        return self.inputs.get("plan", options[0])

    def checkbox(self, label: str) -> bool:
        return self.inputs.get("accepted", False)

    def button(self, label: str) -> bool:
        return label in self.clicks

    def error(self, s: str) -> None:
        self.out.append(("error", s))

    def success(self, s: str) -> None:
        self.out.append(("success", s))

    def markdown(self, s: str) -> None:
        self.out.append(("markdown", s))

    def expander(self, label: str) -> Any:
        import contextlib

        return contextlib.nullcontext()


def _run_streamlit(st: StubStreamlit) -> None:
    """One Streamlit 'rerun': (re)import the script with *st* installed."""
    sys.modules["streamlit"] = st
    sys.modules.pop("streamlit_app", None)
    load_recipe("form_wizard", "streamlit_app")


@pytest.fixture
def clean_modules() -> Any:
    saved = {k: sys.modules.get(k) for k in ("streamlit", "gradio")}
    yield
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:  # pragma: no cover - real library installed
            sys.modules[k] = v
    for k in ("streamlit_app", "gradio_app"):
        sys.modules.pop(k, None)


def test_streamlit_app_walks_the_wizard(clean_modules: Any) -> None:
    session: Dict[str, Any] = {}
    steps = [
        (["Next"], {"email": "bad"}),
        (["Next"], {"email": "a@b.c"}),
        (["Next"], {"plan": "team"}),
        (["Submit"], {"accepted": True}),
        ([], {}),
    ]
    headers, errors = [], []
    for clicks, inputs in steps:
        st = StubStreamlit(clicks, **inputs)
        st.session_state = session  # survives reruns, like the real one
        _run_streamlit(st)
        headers += [s for k, s in st.out if k == "header"]
        errors += [s for k, s in st.out if k == "error"]
        assert any(k == "markdown" and "mermaid" in s for k, s in st.out)
    assert headers[-1].endswith("done")
    assert errors == ["Enter a valid email address."]
    assert ("success", "Welcome, a@b.c (team)!") in st.out


# -- Gradio -------------------------------------------------------------------
def _stub_gradio() -> types.ModuleType:
    gr = types.ModuleType("gradio")
    gr.handlers = []  # type: ignore[attr-defined]

    class Component:
        def __init__(self, *a: Any, **kw: Any) -> None:
            self.args = a

        def click(self, fn: Any, inputs: Any, outputs: Any) -> None:
            gr.handlers.append((self.args[0], fn, len(inputs)))

    class Blocks(Component):
        def __enter__(self) -> "Blocks":
            return self

        def __exit__(self, *exc: Any) -> None:
            return None

        def launch(self) -> None:  # pragma: no cover
            raise AssertionError("never launched in tests")

    for name in ("State", "Markdown", "Textbox", "Radio", "Checkbox"):
        setattr(gr, name, Component)
    gr.Button, gr.Blocks = Component, Blocks  # type: ignore[attr-defined]
    return gr


def test_gradio_app_builds_and_handlers_drive_the_chart(
    clean_modules: Any,
) -> None:
    gr = _stub_gradio()
    sys.modules["gradio"] = gr
    app = load_recipe("form_wizard", "gradio_app")
    assert {label for label, _, _ in gr.handlers} == {"Back", "Next"}
    state, head = app.on_next({}, "a@b.c", "", False)
    assert head.endswith("plan")
    state, head = app.on_back(state)
    assert head.endswith("account")
    state, _ = app.on_next(state, "a@b.c", "", False)
    state, _ = app.on_next(state, "", "free", False)
    state, head = app.on_next(state, "", "", False)  # terms not accepted
    assert head.endswith("confirm")
    state, head = app.on_next(state, "", "", True)
    assert head.endswith("done")


def test_core_imports_no_ui_library() -> None:
    import ast

    tree = ast.parse(open(wz.__file__, encoding="utf-8").read())
    names = {
        (n.module or "") if isinstance(n, ast.ImportFrom) else a.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.Import, ast.ImportFrom))
        for a in n.names
    }
    assert not {"streamlit", "gradio"} & {x.split(".")[0] for x in names}
