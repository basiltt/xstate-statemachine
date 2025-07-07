import asyncio
import json
import logging
from typing import Any, Dict, Tuple

from src.xstate_statemachine import (
    Event,
    Interpreter,
    LoggingInspector,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import ActionDefinition

# -----------------------------------------------------------------------------
# 📚 File Overview
# -----------------------------------------------------------------------------
# This file simulates a cell editor's behavior (e.g., in a spreadsheet
# application) using the `xstate-machine` library. It demonstrates how to
# model complex UI interactions, including text entry, formula editing,
# and automatic/manual "emplace mode" for inserting cell references into
# formulas. The state machine definition is loaded from `cell_editor.json`.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 🪵 Logging Configuration
# -----------------------------------------------------------------------------
# Configures the application's logging to display messages from the
# `xstate-machine` library and the application itself, with informative
# prefixes.
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ⚙️ Action Implementations
# -----------------------------------------------------------------------------


def _start_editing_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Initializes the context when cell editing starts.

    Sets the `editingCell` and `inputValue` based on the event payload.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The 'START_EDITING' event with 'cellId' and 'initialValue'.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    cell_id: Any = event.payload.get("cellId")
    initial_value: str = event.payload.get("initialValue", "")
    context.update(
        {
            "editingCell": cell_id,
            "inputValue": initial_value,
            "isManualEmplaceMode": False,  # Ensure manual mode is off by default
            "caretPosition": len(initial_value),  # Set caret at the end
        }
    )
    logger.info(
        f"📝 Action: Started editing cell '{cell_id}' with value: '{initial_value}'."
    )


def _set_input_value_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Updates the `inputValue` in the context based on user input.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The 'INPUT_CHANGE' event with the new 'value'.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    new_value: Any = event.payload.get("value")
    if new_value is not None:
        context["inputValue"] = new_value
        logger.debug(f"📝 Action: Input value updated to: '{new_value}'.")
    else:
        logger.warning(
            "⚠️ Action: No 'value' found in event payload for setInputValue."
        )


def _update_caret_position_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Updates the `caretPosition` in the context based on the event payload.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event with the new 'position'.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    position: Any = event.payload.get("position")
    if position is not None:
        context["caretPosition"] = position
        logger.debug(f"📝 Action: Caret position updated to: {position}.")
    else:
        logger.warning(
            "⚠️ Action: No 'position' found in event payload for updateCaretPosition."
        )


def _update_emplace_token_by_input_value_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    A no-op action for simulation. In a real application, this would update
    the internal representation of the formula based on the input value.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    logger.debug(
        "👻 Action: updateEmplaceTokenByInputValue (no-op in simulation)."
    )
    pass


def _enable_manual_emplace_mode_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Sets `isManualEmplaceMode` to True, indicating user explicitly entered emplace mode.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    context["isManualEmplaceMode"] = True
    logger.info("⚙️ Action: Manual emplace mode enabled.")


def _disable_manual_emplace_mode_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Sets `isManualEmplaceMode` to False, indicating exit from manual emplace mode.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    context["isManualEmplaceMode"] = False
    logger.info("⚙️ Action: Manual emplace mode disabled.")


def _apply_selection_to_formula_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Appends a selected cell reference to the current `inputValue` (formula).

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The 'SELECTION_CHANGE' event with the 'cellRef'.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    cell_ref: Any = event.payload.get("cellRef")
    if cell_ref:
        context["inputValue"] = context.get("inputValue", "") + cell_ref
        logger.info(
            f"➕ Action: Applied selection '{cell_ref}' to formula. New value: '{context['inputValue']}'."
        )
    else:
        logger.warning(
            "⚠️ Action: No 'cellRef' found in event payload for applySelectionToFormula."
        )


def _finish_editing_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Logs the final input value when editing is finished.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    logger.info(
        f"✅ Action: Editing finished. Final value: '{context.get('inputValue', '')}'."
    )


def _submit_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Logs the submitted input value.

    Args:
        interpreter (Interpreter): The interpreter instance.
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered this action.
        action_def (ActionDefinition): The definition of the action being executed.
    """
    logger.info(
        f"✅ Action: Submitted value: '{context.get('inputValue', '')}'."
    )


# -----------------------------------------------------------------------------
# 🛡️ Guard Implementations
# -----------------------------------------------------------------------------


def _should_enter_emplace_mode_guard(
    context: Dict[str, Any], event: Event
) -> bool:
    """
    Guard that determines if the editor should automatically enter emplace mode.

    Conditions:
    - Not currently in manual emplace mode.
    - The new input value (from event payload) ends with an operator character.

    Args:
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered the guard evaluation.

    Returns:
        bool: True if emplace mode should be entered, False otherwise.
    """
    input_value: str = event.payload.get("value", "")
    is_manual_mode: bool = context.get("isManualEmplaceMode", False)
    operators: Tuple[str, ...] = ("+", "-", "*", "/", "(")

    should_enter: bool = not is_manual_mode and input_value.strip().endswith(
        operators
    )
    logger.debug(
        f"🛡️ Guard 'shouldEnterEmplaceMode': Value ends with operator={should_enter}. "
        f"Input: '{input_value}', Manual Mode: {is_manual_mode}"
    )
    return should_enter


def _should_exit_emplace_mode_guard(
    context: Dict[str, Any], event: Event
) -> bool:
    """
    Guard that determines if the editor should automatically exit emplace mode.

    Conditions:
    - Not currently in manual emplace mode.
    - The new input value (from event payload) ends with a space.

    Args:
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered the guard evaluation.

    Returns:
        bool: True if emplace mode should be exited, False otherwise.
    """
    input_value: str = event.payload.get("value", "")
    is_manual_mode: bool = context.get("isManualEmplaceMode", False)

    should_exit: bool = not is_manual_mode and input_value.endswith(" ")
    logger.debug(
        f"🛡️ Guard 'shouldExitEmplaceMode': Value ends with space={should_exit}. "
        f"Input: '{input_value}', Manual Mode: {is_manual_mode}"
    )
    return should_exit


def _has_editing_cell_guard(context: Dict[str, Any], event: Event) -> bool:
    """
    Guard that checks if there is an `editingCell` ID in the context.

    Args:
        context (Dict[str, Any]): The current context of the state machine.
        event (Event): The event that triggered the guard evaluation.

    Returns:
        bool: True if `editingCell` is not None, False otherwise.
    """
    has_cell: bool = context.get("editingCell") is not None
    logger.debug(f"🛡️ Guard 'hasEditingCell': Cell is being edited={has_cell}.")
    return has_cell


# -----------------------------------------------------------------------------
# 🚀 Main Simulation Logic
# -----------------------------------------------------------------------------


async def main() -> None:
    """
    Loads the cell editor machine and runs simulations for different user
    interaction flows, such as simple text entry and formula creation.
    """
    logger.info("🎬 --- Cell Editor Simulation --- 🎬\n")

    # 📜 Load the machine definition from the JSON file.
    try:
        with open("cell_editor.json", "r") as f:
            cell_editor_config: Dict[str, Any] = json.load(f)
        logger.info(
            "✅ Cell editor machine configuration loaded successfully."
        )
    except FileNotFoundError:
        logger.error(
            "❌ cell_editor.json not found. Please ensure it's in the same directory."
        )
        raise
    except json.JSONDecodeError:
        logger.error(
            "❌ cell_editor.json is malformed. Please check its syntax."
        )
        raise

    # 🧠 Define the implementation logic for the machine by mapping
    # action and guard names from the JSON to concrete Python functions.
    cell_editor_logic = MachineLogic(
        actions={
            "startEditing": _start_editing_action,
            "setInputValue": _set_input_value_action,
            "updateCaretPosition": _update_caret_position_action,
            "updateEmplaceTokenByInputValue": _update_emplace_token_by_input_value_action,
            "enableManualEmplaceMode": _enable_manual_emplace_mode_action,
            "disableManualEmplaceMode": _disable_manual_emplace_mode_action,
            "applySelectionToFormula": _apply_selection_to_formula_action,
            "finishEditing": _finish_editing_action,
            "submit": _submit_action,
        },
        guards={
            "shouldEnterEmplaceMode": _should_enter_emplace_mode_guard,
            "shouldExitEmplaceMode": _should_exit_emplace_mode_guard,
            "hasEditingCell": _has_editing_cell_guard,
        },
    )
    logger.info("✅ Machine logic mapped to cell editor functions.")

    # 🚀 Create the machine definition from the loaded config and logic.
    cell_editor_machine = create_machine(cell_editor_config, cell_editor_logic)
    logger.info("✅ State machine created.")

    # --- Simulation 1: Simple text entry ---
    logger.info("\n🎬 --- Simulation 1: Simple Text Entry --- 🎬")
    interpreter_text: Interpreter = Interpreter(cell_editor_machine)
    interpreter_text.use(LoggingInspector())  # Attach logging inspector
    logger.info("✅ Interpreter for text entry simulation created.")
    await interpreter_text.start()
    logger.info("🏁 Interpreter for text entry simulation started.")

    logger.info("\n--- Step 1: Start editing cell A1 ---")
    await interpreter_text.send(
        "START_EDITING", cellId="A1", initialValue="Hello"
    )
    await asyncio.sleep(0.1)  # Allow event to process and state to update
    print(f"Current State: {interpreter_text.current_state_ids}")
    # 🧪 Validate context update
    print(
        f"Current Value: '{interpreter_text.context.get('inputValue', 'N/A')}'\n"
    )

    logger.info("--- Step 2: User types more text ---")
    await interpreter_text.send("INPUT_CHANGE", value="Hello World")
    await asyncio.sleep(0.1)
    print(f"Current State: {interpreter_text.current_state_ids}")
    # 🧪 Validate context update
    print(
        f"Current Value: '{interpreter_text.context.get('inputValue', 'N/A')}'\n"
    )

    logger.info("--- Step 3: User submits the cell ---")
    await interpreter_text.send("SUBMIT")
    await asyncio.sleep(0.1)
    print(f"Final State: {interpreter_text.current_state_ids}\n")
    await interpreter_text.stop()
    logger.info("🛑 Interpreter for text entry simulation stopped.")

    # --- Simulation 2: Formula entry with automatic emplace mode ---
    logger.info("\n🎬 --- Simulation 2: Formula Entry --- 🎬")
    interpreter_formula: Interpreter = Interpreter(cell_editor_machine)
    interpreter_formula.use(LoggingInspector())  # Attach logging inspector
    logger.info("✅ Interpreter for formula entry simulation created.")
    await interpreter_formula.start()
    logger.info("🏁 Interpreter for formula entry simulation started.")

    logger.info("\n--- Step 1: Start editing and type a formula start ---")
    await interpreter_formula.send(
        "START_EDITING", cellId="B1", initialValue="=A1+"
    )
    await asyncio.sleep(0.1)
    print(
        f"Current State: {interpreter_formula.current_state_ids} (Note: Entered emplace mode automatically)"
    )
    # 🧪 Validate context and state transition
    print(
        f"Current Value: '{interpreter_formula.context.get('inputValue', 'N/A')}'\n"
    )
    logger.debug(f"Current context: {interpreter_formula.context}")

    logger.info(
        "--- Step 2: User clicks another cell to add it to the formula ---"
    )
    await interpreter_formula.send("SELECTION_CHANGE", cellRef="C1")
    await asyncio.sleep(0.1)
    print(f"Current State: {interpreter_formula.current_state_ids}")
    # 🧪 Validate context update (cell reference appended)
    print(
        f"Current Value: '{interpreter_formula.context.get('inputValue', 'N/A')}'\n"
    )
    logger.debug(f"Current context: {interpreter_formula.context}")

    logger.info("--- Step 3: User types a space to exit emplace mode ---")
    # Simulate user typing a space, which triggers 'INPUT_CHANGE'
    current_value_after_selection = interpreter_formula.context.get(
        "inputValue", ""
    )
    await interpreter_formula.send(
        "INPUT_CHANGE", value=current_value_after_selection + " "
    )
    await asyncio.sleep(0.1)
    print(
        f"Current State: {interpreter_formula.current_state_ids} (Note: Exited emplace mode)"
    )
    # 🧪 Validate context and state transition
    print(
        f"Current Value: '{interpreter_formula.context.get('inputValue', 'N/A')}'\n"
    )
    logger.debug(f"Current context: {interpreter_formula.context}")

    logger.info("--- Step 4: User submits the formula ---")
    await interpreter_formula.send("SUBMIT")
    await asyncio.sleep(0.1)
    print(f"Final State: {interpreter_formula.current_state_ids}\n")
    await interpreter_formula.stop()
    logger.info("🛑 Interpreter for formula entry simulation stopped.")


if __name__ == "__main__":
    asyncio.run(main())
