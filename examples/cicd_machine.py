# examples/cicd_machine.py
import asyncio
import logging
import random
from typing import Any, Dict
from uuid import uuid4

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
# This demonstrates how an application using the `xstate-machine` library
# can configure its own logging to see output from the library.
# The library itself does not configure logging, which is the correct practice.
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)


# -----------------------------------------------------------------------------
# 🛠️ Asynchronous Task Helpers
# -----------------------------------------------------------------------------


async def async_task(
    name: str, duration: float = 1.0, failure_chance: float = 0.05
) -> Dict[str, Any]:
    """A generic helper to simulate a cancellable async I/O operation.

    Args:
        name: The name of the task, for logging purposes.
        duration: The base duration for the task to run.
        failure_chance: A float between 0.0 and 1.0 representing the
                        chance this task will fail.

    Returns:
        A dictionary with a success status and the task's duration.

    Raises:
        Exception: If the random failure condition is met.
        asyncio.CancelledError: If the task is cancelled while running.
    """
    print(f"  ▶️  Starting task: {name}...")
    try:
        # Simulate variable I/O time
        await asyncio.sleep(duration * (0.8 + 0.4 * random.random()))

        if random.random() < failure_chance:
            raise Exception(f"Task '{name}' failed due to a random error.")

        result = {"status": "OK", "task": name, "duration": duration}
        print(f"  ✅ Finished task: {name}")
        return result
    except asyncio.CancelledError:
        print(f"  ⏹️  Cancelled task: {name}")
        raise


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------


async def main():
    """
    Configures and runs a complex simulation of a CI/CD pipeline state machine,
    showcasing parallel states, invoked async services, and spawned actors.
    """
    print("🎬 --- CI/CD Pipeline Simulation --- 🎬\n")

    # -------------------------------------------------------------------------
    # 🤖 1. Define the Nested Machine (Actor) for Integration Tests
    # -------------------------------------------------------------------------
    integration_test_config = {
        "id": "integrationTester",
        "initial": "provisioning",
        "context": {"testDb": None, "error": None},
        "states": {
            "provisioning": {
                "invoke": {
                    "src": "provisionTestEnvironment",
                    "onDone": {
                        "target": "runningTests",
                        "actions": ["setTestDb"],
                    },
                    "onError": {
                        "target": "cleanupFailed",
                        "actions": ["logError"],
                    },
                }
            },
            "runningTests": {
                "invoke": {
                    "src": "runIntegrationTests",
                    "onDone": {"target": "deprovisioning"},
                    "onError": {
                        "target": "testsFailed",
                        "actions": ["logError"],
                    },
                }
            },
            "deprovisioning": {
                "invoke": {
                    "src": "deprovisionTestEnvironment",
                    "onDone": {"target": "testsPassed"},
                    "onError": {
                        "target": "cleanupFailed",
                        "actions": ["logError"],
                    },
                }
            },
            "testsPassed": {"type": "final", "entry": ["notifyParentSuccess"]},
            "testsFailed": {"type": "final", "entry": ["notifyParentFailure"]},
            "cleanupFailed": {
                "type": "final",
                "entry": ["notifyParentFailure"],
            },
        },
    }

    # -------------------------------------------------------------------------
    # 🍽️ 2. Define the Main CI/CD Pipeline Machine
    # -------------------------------------------------------------------------
    pipeline_config = {
        "id": "ci-cd-pipeline",
        "initial": "idle",
        "context": {"commitId": None, "artifactUrl": None, "error": None},
        "states": {
            "idle": {
                "on": {
                    "COMMIT_PUSHED": {
                        "target": "initializing",
                        "actions": ["setCommitId"],
                    }
                }
            },
            "initializing": {
                "invoke": {
                    "src": "setupWorkspace",
                    "onDone": "building",
                    "onError": {"target": "failed", "actions": ["logError"]},
                }
            },
            "building": {
                "type": "parallel",
                "onDone": "testing",
                "states": {
                    "buildSteps": {
                        "initial": "installingDeps",
                        "states": {
                            "installingDeps": {
                                "invoke": {
                                    "src": "installDependencies",
                                    "onDone": "compiling",
                                    "onError": "#ci-cd-pipeline.failed",
                                }
                            },
                            "compiling": {
                                "invoke": {
                                    "src": "compileCode",
                                    "onDone": "packaging",
                                    "onError": "#ci-cd-pipeline.failed",
                                }
                            },
                            "packaging": {
                                "invoke": {
                                    "src": "packageArtifacts",
                                    "onDone": {
                                        "target": "done",
                                        "actions": ["setArtifactUrl"],
                                    },
                                    "onError": "#ci-cd-pipeline.failed",
                                }
                            },
                            "done": {"type": "final"},
                        },
                    },
                    "qualityChecks": {
                        "initial": "linting",
                        "states": {
                            "linting": {
                                "invoke": {
                                    "src": "runLinter",
                                    "onDone": "unitTesting",
                                    "onError": "#ci-cd-pipeline.failed",
                                }
                            },
                            "unitTesting": {
                                "invoke": {
                                    "src": "runUnitTests",
                                    "onDone": "done",
                                    "onError": "#ci-cd-pipeline.failed",
                                }
                            },
                            "done": {"type": "final"},
                        },
                    },
                },
            },
            "testing": {
                "entry": ["spawn_integrationTester"],
                "on": {
                    "TESTS_PASSED": "deploying",
                    "TESTS_FAILED": {
                        "target": "failed",
                        "actions": ["logError"],
                    },
                },
            },
            "deploying": {
                "invoke": {
                    "src": "deployToStaging",
                    "onDone": "verifying",
                    "onError": {
                        "target": "deploymentFailed",
                        "actions": ["logError"],
                    },
                }
            },
            "verifying": {
                "invoke": {
                    "src": "runSmokeTests",
                    "onDone": "succeeded",
                    "onError": {
                        "target": "deploymentFailed",
                        "actions": ["logError"],
                    },
                }
            },
            "succeeded": {"type": "final"},
            "failed": {"type": "final"},
            "deploymentFailed": {"type": "final"},
        },
    }

    # -------------------------------------------------------------------------
    # 🧠 3. Define the Implementation Logic (Actions, Services, Guards)
    # -------------------------------------------------------------------------

    # 🤖 Logic for the actor machine.
    integration_test_logic = MachineLogic(
        actions={
            # ⬇️ FIX: Add a fourth argument (e.g., 'action_def') to every lambda ⬇️
            "logError": lambda i, ctx, evt, action_def: ctx.update(
                {"error": str(evt.data)}
            ),
            "setTestDb": lambda i, ctx, evt, action_def: ctx.update(
                {"testDb": evt.data.get("db_url")}
            ),
            # These actions use the `interpreter` to communicate with the parent.
            "notifyParentSuccess": lambda i, ctx, evt, action_def: asyncio.create_task(
                i.parent.send("TESTS_PASSED")
            ),
            "notifyParentFailure": lambda i, ctx, evt, action_def: asyncio.create_task(
                i.parent.send("TESTS_FAILED", error=ctx["error"])
            ),
        },
        services={
            "provisionTestEnvironment": lambda i, c, e: async_task(
                "Provision Test DB", 2, 0.05
            ),
            "runIntegrationTests": lambda i, c, e: async_task(
                "Run Integration Tests", 4, 0.1
            ),
            "deprovisionTestEnvironment": lambda i, c, e: async_task(
                "Deprovision Test DB", 1, 0.02
            ),
        },
    )

    # 🚀 Logic for the main pipeline machine.
    pipeline_logic = MachineLogic(
        actions={
            # ⬇️ FIX: Add a fourth argument (e.g., 'action_def') to every lambda ⬇️
            "setCommitId": lambda i, ctx, evt, action_def: ctx.update(
                {"commitId": evt.payload.get("commitId")}
            ),
            "logError": lambda i, ctx, evt, action_def: ctx.update(
                {"error": str(evt.data)}
            ),
            "setArtifactUrl": lambda i, ctx, evt, action_def: ctx.update(
                {"artifactUrl": evt.data.get("url")}
            ),
        },
        services={
            # Build steps
            "setupWorkspace": lambda i, c, e: async_task("Setup Workspace"),
            "installDependencies": lambda i, c, e: async_task(
                "Install Dependencies", 2
            ),
            "compileCode": lambda i, c, e: async_task("Compile Code", 3),
            "packageArtifacts": lambda i, c, e: async_task(
                "Package Artifacts", 1.5
            ),
            # Quality checks
            "runLinter": lambda i, c, e: async_task("Run Linter", 2.5),
            "runUnitTests": lambda i, c, e: async_task("Run Unit Tests", 4),
            # Deployment
            "deployToStaging": lambda i, c, e: async_task(
                "Deploy to Staging", 5
            ),
            "runSmokeTests": lambda i, c, e: async_task("Run Smoke Tests", 2),
            # This special service provides the machine definition for the actor to be spawned.
            "integrationTester": create_machine(
                integration_test_config, integration_test_logic
            ),
        },
    )

    # -------------------------------------------------------------------------
    # 🚀 4. Create and Run the Simulation
    # -------------------------------------------------------------------------
    pipeline_machine = create_machine(pipeline_config, pipeline_logic)
    interpreter = Interpreter(pipeline_machine)
    interpreter.use(LoggingInspector())
    await interpreter.start()

    print("\n--- 🤖 SIMULATION LOG ---")
    print(f"Initial State: {interpreter.current_state_ids}\n")

    # Kick off the pipeline with a new commit.
    await interpreter.send(
        "COMMIT_PUSHED", commitId=f"commit-{uuid4().hex[:7]}"
    )

    # Let the simulation run to completion. A real application would not have
    # this sleep; it would react to events as they come in over its entire lifecycle.
    await asyncio.sleep(25)

    print("\n--- 🏁 SIMULATION COMPLETE ---")
    print(f"Final State: {interpreter.current_state_ids}")
    print(f"Final Context: {interpreter.context}")

    # Cleanly shut down the interpreter and any actors it spawned.
    await interpreter.stop()


if __name__ == "__main__":
    asyncio.run(main())
