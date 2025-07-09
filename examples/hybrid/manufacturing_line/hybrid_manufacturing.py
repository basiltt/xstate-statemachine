# examples/hybrid_manufacturing.py

# -----------------------------------------------------------------------------
# 🏭 Complex Example: Hybrid Sync & Async Manufacturing Line
# -----------------------------------------------------------------------------
# This script demonstrates a sophisticated use case where an asynchronous
# parent machine (the AssemblyLine) invokes a synchronous child machine
# (the QualityCheck) to get an immediate result before proceeding.
#
# Key Concepts Illustrated:
#   - Hybrid Execution: Combining async and sync interpreters in one system.
#   - Programmatic Invocation: The async machine's action creates and runs the
#     sync machine, inspects its final state, and sends an event to itself.
#   - Pythonic Naming: All functions and logic keys now follow snake_case.
# -----------------------------------------------------------------------------

import asyncio
import json
import logging
import os
import random
from typing import Dict, Any

import sys


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from src.xstate_statemachine import (
    create_machine,
    Interpreter,
    SyncInterpreter,
    MachineLogic,
    Event,
    ActionDefinition,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# -----------------------------------------------------------------------------
# ⚙️ Logic for the Asynchronous AssemblyLine
# -----------------------------------------------------------------------------


async def assemble_part_service(i: Interpreter, c: Dict, e: Event) -> Dict:
    """Async service to simulate assembling a part."""
    logging.info(f"🔧 Assembling part {c['partId']}... (3 seconds)")
    await asyncio.sleep(3)
    return {"status": "assembled"}


async def package_part_service(i: Interpreter, c: Dict, e: Event) -> Dict:
    """Async service to simulate packaging a part."""
    logging.info(f"📦 Packaging part {c['partId']}... (2 seconds)")
    await asyncio.sleep(2)
    return {"status": "packaged"}


def assign_part_id_action(
    i: Interpreter, c: Dict, e: Event, a: ActionDefinition
) -> None:
    """Action to assign the part ID to the context."""
    c["partId"] = e.payload.get("partId")
    logging.info(f"🔩 Part {c['partId']} received on assembly line.")


# -----------------------------------------------------------------------------
# ⚙️ Logic for the Synchronous QualityCheck Machine
# -----------------------------------------------------------------------------


def run_inspection_action(
    i: SyncInterpreter, c: Dict, e: Event, a: ActionDefinition
) -> None:
    """Action for the sync machine to run a quality inspection."""
    logging.info("🔬 [QC] Running synchronous inspection...")
    c["inspectionCount"] += 1
    c["isPassed"] = random.random() > 0.2  # 80% chance of passing


def did_pass_guard(c: Dict, e: Event) -> bool:
    """Guard for the sync machine to check if the part passed."""
    return c["isPassed"]


def set_passed_action(
    i: SyncInterpreter, c: Dict, e: Event, a: ActionDefinition
) -> None:
    """Action for the sync machine to log a successful check."""
    logging.info("✅ [QC] Part has passed quality check.")


# -----------------------------------------------------------------------------
# 🚀 Hybrid Orchestration Action
# -----------------------------------------------------------------------------


def run_quality_check_action(
    interpreter: Interpreter,
    context: Dict,
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    An action on the ASYNC machine that creates and runs the SYNC QC machine.
    """
    logging.info("----------")
    logging.info(
        "🔍 Entering Quality Control. Running synchronous QC check..."
    )

    # 1. Load the synchronous machine's config
    with open("quality_check_sync.json", "r") as f:
        qc_config = json.load(f)

    # 2. Define its logic using snake_case keys
    qc_logic = MachineLogic(
        actions={
            "run_inspection": run_inspection_action,
            "set_passed": set_passed_action,
        },
        guards={"did_pass": did_pass_guard},
    )

    # 3. Create and run the SYNC interpreter
    qc_machine = create_machine(qc_config, logic=qc_logic)
    qc_interpreter = SyncInterpreter(qc_machine).start()

    # 4. Check the final state of the sync machine to get the result
    if "qualityCheck.passed" in qc_interpreter.current_state_ids:
        context["qcResult"] = "PASSED"
        # 5. Send an event back to the parent async machine
        asyncio.create_task(interpreter.send("QC_PASSED"))
    else:
        context["qcResult"] = "FAILED"
        asyncio.create_task(interpreter.send("QC_FAILED"))

    logging.info(
        f"🏁 Synchronous QC check complete. Result: {context['qcResult']}"
    )
    logging.info("----------")


async def main():
    """Runs the hybrid manufacturing simulation."""
    print("\n--- 🏭 Hybrid Sync/Async Manufacturing Line ---")

    with open("manufacturing_line_async.json", "r") as f:
        assembly_config = json.load(f)

    assembly_logic = MachineLogic(
        actions={
            "assign_part_id": assign_part_id_action,
            "run_quality_check": run_quality_check_action,
        },
        services={
            "assemble_part": assemble_part_service,
            "package_part": package_part_service,
        },
    )

    assembly_machine = create_machine(assembly_config, logic=assembly_logic)
    interpreter = await Interpreter(assembly_machine).start()

    logging.info("▶️ Starting production for part #P-123")
    await interpreter.send("PART_RECEIVED", partId="P-123")

    # Wait for the entire async process to finish
    await asyncio.sleep(8)

    logging.info("\n✅ Production run complete.")
    logging.info(f"Final State: {interpreter.current_state_ids}")
    logging.info(f"Final Context: {interpreter.context}")

    await interpreter.stop()


if __name__ == "__main__":
    asyncio.run(main())
