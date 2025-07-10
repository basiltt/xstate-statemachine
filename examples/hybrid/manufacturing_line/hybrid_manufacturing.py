# examples/hybrid/manufacturing_line/hybrid_manufacturing.py
# -------------------------------------------------------------------------------
# 🏭 Complex Example: Hybrid Sync & Async Manufacturing Line
# -------------------------------------------------------------------------------
"""
Demonstrates a hybrid manufacturing workflow combining:

  • 🔧 AssemblyLine (async): assembles and packages parts.
  • 🔬 QualityCheck (sync): runs an immediate quality inspection.
  • ↔️ Hybrid Execution: an async action spins up a sync interpreter,
       inspects its final state, and feeds the result back into the async flow.

Key Concepts:
  - Programmatic Invocation of SyncInterpreter from async code.
  - Event-driven handoff of synchronous results back to the async machine.
  - Snake_case naming, rich emoji logging, and Google-style docstrings.
"""

import asyncio
import json
import logging
import os
import random
import sys
from typing import Any, Dict

from src.xstate_statemachine import (
    create_machine,
    Event,
    Interpreter,
    MachineLogic,
    ActionDefinition,
    SyncInterpreter,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure the examples folder is on the path for JSON imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# -----------------------------------------------------------------------------
# 🔧 AssemblyLine Logic (Async Services & Actions)
# -----------------------------------------------------------------------------


async def assemble_part_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """🔩 Simulate part assembly over 3 seconds.

    Args:
        interpreter: The running async interpreter.
        context: Mutable machine context.
        event: Triggering PART_RECEIVED event.

    Returns:
        A dict indicating assembly status.
    """
    part_id = context.get("partId")
    logger.info(f"🔧 Assembling part '{part_id}' (3s)...")
    await asyncio.sleep(3)
    return {"status": "assembled"}


async def package_part_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """📦 Simulate part packaging over 2 seconds.

    Args:
        interpreter: The running async interpreter.
        context: Mutable machine context.
        event: Triggering ASSEMBLY_COMPLETE event.

    Returns:
        A dict indicating packaging status.
    """
    part_id = context.get("partId")
    logger.info(f"📦 Packaging part '{part_id}' (2s)...")
    await asyncio.sleep(2)
    return {"status": "packaged"}


def assign_part_id_action(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🆔 Store the incoming part ID into context.

    Args:
        interpreter: The running async interpreter.
        context: Mutable machine context.
        event: Triggering PART_RECEIVED event carrying payload {'partId'}.
        action_def: Metadata for this action.
    """
    part_id = event.payload.get("partId")
    context["partId"] = part_id
    logger.info(f"🔩 Part '{part_id}' received on assembly line.")


# -----------------------------------------------------------------------------
# 🔬 QualityCheck Logic (Sync Actions & Guards)
# -----------------------------------------------------------------------------


def run_inspection_action(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔬 Perform a synchronous quality inspection.

    Args:
        interpreter: The SyncInterpreter instance.
        context: Mutable machine context for QC.
        event: Internal inspection trigger.
        action_def: Metadata for this action.
    """
    context["inspectionCount"] += 1
    context["isPassed"] = random.random() > 0.2  # 80% pass rate
    logger.info("🔬 [QC] Inspection executed.")


def did_pass_guard(
    context: Dict[str, Any],
    event: Event,  # noqa
) -> bool:
    """✔️ Guard: Check if the part passed QC.

    Args:
        context: Mutable machine context for QC.
        event: Internal inspection trigger.

    Returns:
        True if the part passed; False otherwise.
    """
    passed = bool(context.get("isPassed"))
    logger.info(f"✔️ [QC] did_pass_guard -> {passed}")
    return passed


def set_passed_action(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """✅ Log successful quality check.

    Args:
        interpreter: The SyncInterpreter instance.
        context: Mutable machine context for QC.
        event: onDone QC transition.
        action_def: Metadata for this action.
    """
    logger.info("✅ [QC] Part passed quality check.")


# -----------------------------------------------------------------------------
# 🔄 Hybrid Orchestration Action
# -----------------------------------------------------------------------------


def run_quality_check_action(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """↔️ Spawn and run the sync QC machine, then feed its result back.

    Args:
        interpreter: The running async interpreter.
        context: Mutable async machine context.
        event: Triggering QC_RUN event.
        action_def: Metadata for this action.
    """
    logger.info("----------")
    logger.info("🔍 Running synchronous QualityCheck...")

    # Load sync machine definition
    qc_path = os.path.join(
        os.path.dirname(__file__), "quality_check_sync.json"
    )
    with open(qc_path, "r", encoding="utf-8") as f:
        qc_config = json.load(f)

    # Build its logic
    qc_logic = MachineLogic(
        actions={
            "run_inspection": run_inspection_action,
            "set_passed": set_passed_action,
        },
        guards={"did_pass": did_pass_guard},
    )

    # Create & start SyncInterpreter
    qc_machine = create_machine(qc_config, logic=qc_logic)
    qc_interpreter = SyncInterpreter(qc_machine)
    qc_interpreter.start()

    # Inspect the final state and dispatch back to async flow
    final_states = qc_interpreter.current_state_ids
    if "qualityCheck.passed" in final_states:
        context["qcResult"] = "PASSED"
        asyncio.create_task(interpreter.send("QC_PASSED"))
    else:
        context["qcResult"] = "FAILED"
        asyncio.create_task(interpreter.send("QC_FAILED"))

    logger.info(f"🏁 QC result: {context['qcResult']}")
    logger.info("----------")


# -----------------------------------------------------------------------------
# 🚀 Main Entry Point
# -----------------------------------------------------------------------------


async def main() -> None:
    """🚀 Launch the hybrid manufacturing simulation."""
    logger.info("\n--- 🏭 Hybrid Manufacturing Line Start ---")

    # Load async machine config
    asm_path = os.path.join(
        os.path.dirname(__file__), "manufacturing_line_async.json"
    )
    with open(asm_path, "r", encoding="utf-8") as f:
        asm_config = json.load(f)

    # Bind async logic
    asm_logic = MachineLogic(
        actions={
            "assign_part_id": assign_part_id_action,
            "run_quality_check": run_quality_check_action,
        },
        services={
            "assemble_part": assemble_part_service,
            "package_part": package_part_service,
        },
    )

    # Create and start async interpreter
    assembly_machine = create_machine(asm_config, logic=asm_logic)
    interpreter = await Interpreter(assembly_machine).start()

    # Kick off the production run
    part_id = "P-123"
    logger.info(f"▶️ Sending PART_RECEIVED('{part_id}')")
    await interpreter.send("PART_RECEIVED", partId=part_id)

    # Allow time for full assembly→QC→packaging flow
    await asyncio.sleep(8)

    logger.info("✅ Production run complete.")
    logger.info(f"Final States: {interpreter.current_state_ids}")
    logger.info(f"Final Context: {interpreter.context}")

    await interpreter.stop()
    logger.info("--- Simulation End ---")


if __name__ == "__main__":
    asyncio.run(main())
