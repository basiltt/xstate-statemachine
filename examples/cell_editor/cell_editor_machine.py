# examples/cell_editor_machine.py
import asyncio
import json
import logging
from typing import Any, Dict

from src.xstate_machine import (
    Event,
    Interpreter,
    LoggingInspector,
    MachineLogic,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🪵 Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------


async def main():
    """
    Loads the cell editor machine and runs simulations for different user
    interaction flows, such as simple text entry and formula creation.
    """
    print("🎬 --- Cell Editor Simulation --- 🎬\n")

    # 📜 Load the machine definition from the JSON file.
    with open("cell_editor.json") as f:
        cell_editor_config = json.load(f)

    # 🧠 Define the implementation logic for the machine.
    cell_editor_logic = MachineLogic(
        actions={
            "startEditing": lambda i, ctx, evt: ctx.update(
                {
                    "editingCell": evt.payload.get("cellId"),
                    "inputValue": evt.payload.get("initialValue", ""),
                }
            ),
            "setInputValue": lambda i, ctx, evt: ctx.update(
                {"inputValue": evt.payload.get("value")}
            ),
            "updateCaretPosition": lambda i, ctx, evt: ctx.update(
                {"caretPosition": evt.payload.get("position")}
            ),
            "updateEmplaceTokenByInputValue": lambda i, ctx, evt: None,  # No-op for simulation
            "enableManualEmplaceMode": lambda i, ctx, evt: ctx.update(
                {"isManualEmplaceMode": True}
            ),
            "disableManualEmplaceMode": lambda i, ctx, evt: ctx.update(
                {"isManualEmplaceMode": False}
            ),
            "applySelectionToFormula": lambda i, ctx, evt: ctx.update(
                {"inputValue": ctx["inputValue"] + evt.payload.get("cellRef")}
            ),
            "finishEditing": lambda i, ctx, evt: print(
                f"✅ Editing finished. Final value: '{ctx['inputValue']}'"
            ),
            "submit": lambda i, ctx, evt: print(
                f"✅ Submitted value: '{ctx['inputValue']}'"
            ),
        },
        guards={
            # Enter emplace mode if input ends with an operator (and not manual mode).
            "shouldEnterEmplaceMode": lambda ctx, evt: (
                not ctx["isManualEmplaceMode"]
                and evt.payload.get("value", "")
                .strip()
                .endswith(tuple("+-*/("))
            ),
            # Exit emplace mode if a space is typed (and not manual mode).
            "shouldExitEmplaceMode": lambda ctx, evt: (
                not ctx["isManualEmplaceMode"]
                and evt.payload.get("value", "").endswith(" ")
            ),
            "hasEditingCell": lambda ctx, evt: ctx.get("editingCell")
            is not None,
        },
    )

    # 🚀 Create the machine definition from the loaded config and logic.
    cell_editor_machine = create_machine(cell_editor_config, cell_editor_logic)

    # --- Simulation 1: Simple text entry ---
    print("\n🎬 --- Simulation 1: Simple Text Entry --- 🎬")
    interpreter_text = Interpreter(cell_editor_machine)
    interpreter_text.use(LoggingInspector())
    await interpreter_text.start()

    print("\n--- Step 1: Start editing cell A1 ---")
    await interpreter_text.send(
        "START_EDITING", cellId="A1", initialValue="Hello"
    )
    await asyncio.sleep(0.1)
    print(f"Current State: {interpreter_text.current_state_ids}")
    print(f"Current Value: '{interpreter_text.context['inputValue']}'\n")

    print("--- Step 2: User types more text ---")
    await interpreter_text.send("INPUT_CHANGE", value="Hello World")
    await asyncio.sleep(0.1)
    print(f"Current State: {interpreter_text.current_state_ids}")
    print(f"Current Value: '{interpreter_text.context['inputValue']}'\n")

    print("--- Step 3: User submits the cell ---")
    await interpreter_text.send("SUBMIT")
    await asyncio.sleep(0.1)
    print(f"Final State: {interpreter_text.current_state_ids}\n")
    await interpreter_text.stop()

    # --- Simulation 2: Formula entry with automatic emplace mode ---
    print("\n🎬 --- Simulation 2: Formula Entry --- 🎬")
    interpreter_formula = Interpreter(cell_editor_machine)
    interpreter_formula.use(LoggingInspector())
    await interpreter_formula.start()

    print("\n--- Step 1: Start editing and type a formula start ---")
    await interpreter_formula.send(
        "START_EDITING", cellId="B1", initialValue="=A1+"
    )
    await asyncio.sleep(0.1)
    print(
        f"Current State: {interpreter_formula.current_state_ids} (Note: Entered emplace mode automatically)"
    )
    print(f"Current Value: '{interpreter_formula.context['inputValue']}'\n")

    print("--- Step 2: User clicks another cell to add it to the formula ---")
    await interpreter_formula.send("SELECTION_CHANGE", cellRef="C1")
    await asyncio.sleep(0.1)
    print(f"Current State: {interpreter_formula.current_state_ids}")
    print(f"Current Value: '{interpreter_formula.context['inputValue']}'\n")

    print("--- Step 3: User types a space to exit emplace mode ---")
    await interpreter_formula.send(
        "INPUT_CHANGE", value=interpreter_formula.context["inputValue"] + " "
    )
    await asyncio.sleep(0.1)
    print(
        f"Current State: {interpreter_formula.current_state_ids} (Note: Exited emplace mode)"
    )
    print(f"Current Value: '{interpreter_formula.context['inputValue']}'\n")

    print("--- Step 4: User submits the formula ---")
    await interpreter_formula.send("SUBMIT")
    await asyncio.sleep(0.1)
    print(f"Final State: {interpreter_formula.current_state_ids}\n")
    await interpreter_formula.stop()


if __name__ == "__main__":
    asyncio.run(main())
