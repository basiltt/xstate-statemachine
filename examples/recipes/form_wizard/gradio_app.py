# examples/recipes/form_wizard/gradio_app.py
"""Gradio front end: ``python gradio_app.py``.

Each click handler receives the per-user ``gr.State`` dict, applies one
event through `Wizard`, and returns the new state plus the step header.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import gradio as gr

from wizard import PLANS, Wizard, diagram


def _header(wiz: Wizard) -> str:
    return f"## Sign up -- {wiz.step}"


def on_next(
    state: Dict, email: str, plan: str, accepted: bool
) -> Tuple[Dict, str]:
    state = dict(state or {})
    wiz = Wizard(state)
    fields: Dict[str, Any] = {
        "account": {"email": email},
        "plan": {"plan": plan},
        "confirm": {"accepted": accepted},
    }.get(wiz.step, {})
    event = "SUBMIT" if wiz.step == "confirm" else "NEXT"
    wiz.send(event, **fields)
    return state, _header(wiz)


def on_back(state: Dict) -> Tuple[Dict, str]:
    state = dict(state or {})
    wiz = Wizard(state)
    wiz.send("BACK")
    return state, _header(wiz)


with gr.Blocks(title="Signup wizard") as demo:
    session = gr.State({})
    header = gr.Markdown("## Sign up -- account")
    email_in = gr.Textbox(label="Email")
    plan_in = gr.Radio(list(PLANS), label="Plan")
    terms_in = gr.Checkbox(label="I accept the terms")
    back, nxt = gr.Button("Back"), gr.Button("Next")
    gr.Markdown(f"```mermaid\n{diagram()}\n```")
    nxt.click(
        on_next, [session, email_in, plan_in, terms_in], [session, header]
    )
    back.click(on_back, [session], [session, header])


if __name__ == "__main__":  # pragma: no cover
    demo.launch()
