# examples/recipes/form_wizard/streamlit_app.py
"""Streamlit front end: ``streamlit run streamlit_app.py``.

Streamlit re-executes this file on every interaction; the wizard's
snapshot survives in ``st.session_state``.
"""

from __future__ import annotations

import streamlit as st

from wizard import PLANS, Wizard, diagram


def render() -> None:
    wiz = Wizard(st.session_state)
    step = wiz.step
    st.header(f"Sign up -- {step}")
    if step == "account":
        email = st.text_input("Email", value=wiz.data["email"])
        if st.button("Next") and not wiz.send("NEXT", email=email):
            st.error("Enter a valid email address.")
    elif step == "plan":
        plan = st.radio("Plan", PLANS)
        if st.button("Back"):
            wiz.send("BACK")
        elif st.button("Next"):
            wiz.send("NEXT", plan=plan)
    elif step == "confirm":
        accepted = st.checkbox("I accept the terms")
        if st.button("Back"):
            wiz.send("BACK")
        elif st.button("Submit") and not wiz.send("SUBMIT", accepted=accepted):
            st.error("Please accept the terms.")
    else:
        st.success(f"Welcome, {wiz.data['email']} ({wiz.data['plan']})!")
    with st.expander("How this form works"):
        st.markdown(f"```mermaid\n{diagram()}\n```")


render()
