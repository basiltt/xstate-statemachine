---
title: "Recipe: Streamlit / Gradio wizard"
permalink: /guide/form-wizard/
description: "A multi-step form whose steps, back/forward navigation and validation live in a statechart. Only its JSON snapshot is kept in st.session_state or gr.State. The diagram is embedded in the app."
---

# Recipe: Streamlit / Gradio wizard

Multi-step forms in Streamlit and Gradio usually end up as a `step` integer and a thicket of `if`s: which step comes after which, when *Next* is allowed, and what *Back* keeps. Put those rules in a chart instead. **Back** and **Next** are events, validation is a guard on `NEXT`, and the UI only renders whichever step is active.

Both frameworks rerun your code on every click, so the wizard keeps **only the snapshot**, a JSON string. It lives in `st.session_state` or in a `gr.State` dict. Each click is *restore → send → snapshot*.

Files: [`examples/recipes/form_wizard/`](https://github.com/basiltt/xstate-statemachine/tree/main/examples/recipes/form_wizard). `wizard.py` holds the framework-free core. `streamlit_app.py` and `gradio_app.py` are the front ends.

```bash
xsm simulate examples/recipes/form_wizard/machine.json --events NEXT,BACK,NEXT,NEXT,SUBMIT
# -> signup.done    (every guard stubbed True; add --guards-false accountValid to see NEXT refused)
xsm diagram examples/recipes/form_wizard/machine.json      # the Mermaid the apps embed
```

## The core

```python
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine

chart = {"id": "signup", "initial": "account", "context": {"email": "", "plan": ""}, "states": {
    "account": {"on": {"NEXT": {"target": "plan", "guard": "accountValid", "actions": "save"}}},
    "plan": {"on": {"BACK": "account", "NEXT": {"target": "done", "guard": "planChosen", "actions": "save"}}},
    "done": {"type": "final"}}}
def save(i, ctx, e, a): ctx.update({k: v for k, v in e.payload.items() if k in ctx})
machine = create_machine(chart, logic=MachineLogic(actions={"save": save}, guards={
    "accountValid": lambda ctx, e: "@" in e.payload.get("email", ""),
    "planChosen": lambda ctx, e: e.payload.get("plan") in ("free", "pro")}))

def click(session: dict, event: str, **fields) -> bool:
    """One UI interaction: restore -> send -> snapshot. False = input refused."""
    blob = session.get("wizard")
    i = (SyncInterpreter.from_snapshot(blob, machine) if blob else SyncInterpreter(machine)).start()
    changed = i.send(event, wait=True, **fields).changed
    session["wizard"] = i.get_snapshot()      # a JSON string: session-state safe
    i.stop()
    return changed

session = {}                                  # st.session_state / the dict in gr.State
assert click(session, "NEXT", email="nope") is False     # the guard refuses; show an error
assert click(session, "NEXT", email="ann@example.com")
assert click(session, "BACK") and click(session, "NEXT", email="ann@example.com")
assert click(session, "NEXT", plan="pro")
assert '"done"' in session["wizard"]
```

`wizard.Wizard(session)` in the example wraps exactly this, and adds `.step`, `.data` and `diagram()`.

## Streamlit

<!-- doc-fragment -->
```python
import streamlit as st
from wizard import PLANS, Wizard, diagram

wiz = Wizard(st.session_state)
st.header(f"Sign up -- {wiz.step}")
if wiz.step == "account":
    email = st.text_input("Email", value=wiz.data["email"])
    if st.button("Next") and not wiz.send("NEXT", email=email):
        st.error("Enter a valid email address.")
elif wiz.step == "plan":
    plan = st.radio("Plan", PLANS)
    if st.button("Back"):
        wiz.send("BACK")
    elif st.button("Next"):
        wiz.send("NEXT", plan=plan)
# ... confirm / done ...
with st.expander("How this form works"):
    st.markdown(f"```mermaid\n{diagram()}\n```")    # the chart, embedded
```

## Gradio

<!-- doc-fragment -->
```python
import gradio as gr
from wizard import PLANS, Wizard, diagram

def on_next(state, email, plan, accepted):
    state = dict(state or {}); wiz = Wizard(state)
    fields = {"account": {"email": email}, "plan": {"plan": plan},
              "confirm": {"accepted": accepted}}.get(wiz.step, {})
    wiz.send("SUBMIT" if wiz.step == "confirm" else "NEXT", **fields)
    return state, f"## Sign up -- {wiz.step}"

with gr.Blocks() as demo:
    session = gr.State({})
    header = gr.Markdown("## Sign up -- account")
    email, plan, terms = gr.Textbox(label="Email"), gr.Radio(list(PLANS)), gr.Checkbox()
    gr.Button("Next").click(on_next, [session, email, plan, terms], [session, header])
    gr.Markdown(f"```mermaid\n{diagram()}\n```")
```

Neither library is a dependency. `tests/recipes/test_form_wizard.py` imports both apps against stub `streamlit` and `gradio` modules. It clicks through the whole wizard, refused input included, and checks that the Mermaid diagram is rendered.

## Why a chart here

- **Back keeps data.** `BACK` is a plain transition, so the context, and with it everything typed so far, is untouched.
- **Validation is declarative.** `NEXT` has a guard. A refused `NEXT` returns `changed=False` and your UI shows the error. No step counter can drift out of range.
- **Adding a step is a chart edit.** Draw it in Stately, re-export `machine.json`, and add one `elif` for its widgets.
- **The session is small and serializable.** It is a JSON string, not live objects, so it survives Streamlit reruns and Gradio queueing.

Related: [Flask session-keyed wizards](../integration-flask/), [Diagrams](../diagrams/), [all recipes](../recipes/).
