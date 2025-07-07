"""
examples/cicd_machine.py
-------
A complex simulation of a CI/CD pipeline using the XState machine library.

This script demonstrates various advanced features of the state machine,
including nested states, parallel states, invoked services, delayed transitions,
guards, actions, and actor spawning/communication.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import random
from typing import Any, Dict, Optional
from uuid import uuid4

from src.xstate_statemachine import (
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
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Asynchronous Task Helpers
# -----------------------------------------------------------------------------


async def async_task(
    name: str,
    duration: float = 1.0,
    failure_chance: float = 0.05,
    result_data: Optional[
        Dict[str, Any]
    ] = None,  # ✅ Added for custom results
) -> Dict[str, Any]:
    """
    A generic helper to simulate a cancellable asynchronous I/O operation.

    This function mimics a typical long-running operation in a CI/CD pipeline,
    such as compiling code, running tests, or deploying. It includes
    simulated latency and a configurable chance of failure.

    Args:
        name (str): The name of the task, used for logging purposes.
        duration (float): The base duration for the task to run in seconds.
                          The actual duration will vary slightly. Defaults to 1.0.
        failure_chance (float): A float between 0.0 and 1.0 representing the
                                chance this task will fail. Defaults to 0.05.
        result_data (Optional[Dict[str, Any]]): An optional dictionary to merge
                                                  into the successful result. This
                                                  allows tasks to return specific data.

    Returns:
        Dict[str, Any]: A dictionary containing the task's status, name, and duration
                        if the task completes successfully. Custom `result_data` is merged.

    Raises:
        Exception: If the random failure condition is met, indicating a task failure.
        asyncio.CancelledError: If the task is cancelled (e.g., by the state machine
                                moving to a different state or being stopped) while running.
    """
    logger.info(f"  ▶️ Starting task: {name}...")
    try:
        # Simulate variable I/O time
        await asyncio.sleep(duration * (0.8 + 0.4 * random.random()))

        if random.random() < failure_chance:
            logger.error(f"  ❌ Task '{name}' failed due to a random error.")
            raise Exception(f"Task '{name}' failed due to a random error.")

        result = {"status": "OK", "task": name, "duration": duration}
        if result_data:
            result.update(result_data)  # 🧩 Merge any custom result data

        logger.info(f"  ✅ Finished task: {name}")
        return result
    except asyncio.CancelledError:
        logger.warning(f"  ⏹️ Cancelled task: {name}")
        raise
    except Exception as e:
        logger.error(f"  ‼️ Task '{name}' encountered an error: {e}")
        raise


# -----------------------------------------------------------------------------
# Machine Configurations
# -----------------------------------------------------------------------------


def get_integration_test_config() -> Dict[str, Any]:
    """
    Returns the configuration dictionary for the Integration Test state machine (actor).

    This machine simulates the lifecycle of running integration tests, including
    environment provisioning, test execution, and deprovisioning. It's designed
    to be spawned as a child actor by the main CI/CD pipeline.

    Returns:
        Dict[str, Any]: The configuration for the integration test actor machine.
    """
    return {
        "id": "integrationTester",
        "initial": "provisioning",
        "context": {
            "testDb": None,
            "error": None,
        },  # Context for test environment details
        "states": {
            "provisioning": {
                "invoke": {
                    "src": "provisionTestEnvironment",  # 📞 Provision DB asynchronously
                    "onDone": {
                        "target": "runningTests",
                        "actions": [
                            "setTestDb"
                        ],  # ✅ On success, store DB info
                    },
                    "onError": {
                        "target": "cleanupFailed",
                        "actions": ["logError"],  # ❌ On failure, log error
                    },
                }
            },
            "runningTests": {
                "invoke": {
                    "src": "runIntegrationTests",  # 📞 Run tests asynchronously
                    "onDone": {
                        "target": "deprovisioning"
                    },  # ✅ On success, deprovision
                    "onError": {
                        "target": "testsFailed",
                        "actions": [
                            "logError"
                        ],  # ❌ On failure, mark tests failed
                    },
                }
            },
            "deprovisioning": {
                "invoke": {
                    "src": "deprovisionTestEnvironment",  # 📞 Deprovision DB asynchronously
                    "onDone": {
                        "target": "testsPassed"
                    },  # ✅ On success, tests passed
                    "onError": {
                        "target": "cleanupFailed",
                        "actions": [
                            "logError"
                        ],  # ❌ On failure, mark cleanup failed
                    },
                }
            },
            "testsPassed": {
                "type": "final",
                "entry": ["notifyParentSuccess"],
            },  # 🎉 Final success state
            "testsFailed": {
                "type": "final",
                "entry": ["notifyParentFailure"],
            },  # 🛑 Final failure state
            "cleanupFailed": {
                "type": "final",
                "entry": [
                    "notifyParentFailure"
                ],  # 🧹 Final state for cleanup issues
            },
        },
    }


def get_pipeline_config() -> Dict[str, Any]:
    """
    Returns the configuration dictionary for the main CI/CD Pipeline state machine.

    This machine defines the entire workflow of a CI/CD pipeline, including
    initialization, parallel build and quality checks, testing, deployment,
    and final verification.

    Returns:
        Dict[str, Any]: The configuration for the CI/CD pipeline machine.
    """
    return {
        "id": "ci-cd-pipeline",
        "initial": "idle",
        "context": {
            "commitId": None,
            "artifactUrl": None,
            "error": None,
        },  # Pipeline context
        "states": {
            "idle": {
                "on": {
                    "COMMIT_PUSHED": {
                        "target": "initializing",
                        "actions": [
                            "setCommitId"
                        ],  # ➡️ Start pipeline on commit
                    }
                }
            },
            "initializing": {
                "invoke": {
                    "src": "setupWorkspace",  # 📞 Setup environment
                    "onDone": "building",  # ✅ Move to building
                    "onError": {
                        "target": "failed",
                        "actions": ["logError"],
                    },  # ❌ Handle failure
                }
            },
            "building": {
                "type": "parallel",  # 👯 Run build steps and quality checks concurrently
                "onDone": "testing",  # ✅ When both parallel states are done, move to testing
                "states": {
                    "buildSteps": {
                        "initial": "installingDeps",
                        "states": {
                            "installingDeps": {
                                "invoke": {
                                    "src": "installDependencies",
                                    "onDone": "compiling",
                                    "onError": "#ci-cd-pipeline.failed",  # 🛑 Fail entire pipeline
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
                                        "actions": [
                                            "setArtifactUrl"
                                        ],  # ✅ Store artifact URL
                                    },
                                    "onError": "#ci-cd-pipeline.failed",
                                }
                            },
                            "done": {
                                "type": "final"
                            },  # 🎉 Final state for build steps
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
                            "done": {
                                "type": "final"
                            },  # 🎉 Final state for quality checks
                        },
                    },
                },
            },
            "testing": {
                "entry": [
                    "spawn_integrationTester"
                ],  # 👶 Spawn child actor for integration tests
                "on": {
                    "TESTS_PASSED": "deploying",  # ✅ If tests pass, proceed to deploy
                    "TESTS_FAILED": {
                        "target": "failed",
                        "actions": [
                            "logError"
                        ],  # ❌ If tests fail, mark pipeline as failed
                    },
                },
            },
            "deploying": {
                "invoke": {
                    "src": "deployToStaging",  # 📞 Deploy the artifact
                    "onDone": "verifying",  # ✅ On success, verify deployment
                    "onError": {
                        "target": "deploymentFailed",
                        "actions": ["logError"],
                    },
                }
            },
            "verifying": {
                "invoke": {
                    "src": "runSmokeTests",  # 📞 Run smoke tests on deployed app
                    "onDone": "succeeded",  # ✅ On success, pipeline succeeded
                    "onError": {
                        "target": "deploymentFailed",
                        "actions": ["logError"],
                    },
                }
            },
            "succeeded": {"type": "final"},  # 🎉 Overall pipeline success
            "failed": {
                "type": "final"
            },  # 🛑 Overall pipeline failure (build/test related)
            "deploymentFailed": {
                "type": "final"
            },  # ⚠️ Overall pipeline failure (deployment/verification related)
        },
    }


# -----------------------------------------------------------------------------
# Machine Logic (Actions, Services, Guards)
# -----------------------------------------------------------------------------


class IntegrationTestLogic(MachineLogic):
    """
    Encapsulates custom logic (actions, services, guards) for the Integration Tester state machine.

    This class provides the implementation for tasks related to provisioning,
    running, and deprovisioning test environments, as well as communicating
    results back to the parent CI/CD pipeline.
    """

    def __init__(self):
        """Initializes the IntegrationTestLogic."""
        super().__init__()
        self._setup_actions()
        self._setup_services()

    def _setup_actions(self) -> None:
        """
        Defines and sets up all action functions used by the integration test machine.

        Actions are side effects performed during state transitions or on entry/exit of states.
        Each action receives the interpreter, context, event, and action definition.
        """
        self.actions = {
            "logError": self._log_error,
            "setTestDb": self._set_test_db,
            "notifyParentSuccess": self._notify_parent_success,
            "notifyParentFailure": self._notify_parent_failure,
        }

    def _setup_services(self) -> None:
        """
        Defines and sets up all service functions used by the integration test machine.

        Services are asynchronous operations invoked by states. They can be
        other state machines (actors) or external async functions.
        """
        self.services = {
            "provisionTestEnvironment": lambda i, c, e: async_task(
                "Provision Test DB",
                2,
                0.05,
                result_data={
                    "db_url": "postgresql://test_user:pass@test_db:5432/test_ci_db"
                },  # ✅ Example data
            ),
            "runIntegrationTests": lambda i, c, e: async_task(
                "Run Integration Tests", 4, 0.1
            ),
            "deprovisionTestEnvironment": lambda i, c, e: async_task(
                "Deprovision Test DB", 1, 0.02
            ),
        }

    # --- Actions ---
    def _log_error(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Logs an error message and updates the context with the error details.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this action, containing error data.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        error_data = evt.data
        ctx.update({"error": str(error_data)})
        logger.error(f"❌ Integration test error: {error_data}")

    def _set_test_db(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Sets the test database URL in the integration tester's context.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event containing the database URL data.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        db_url = evt.data.get("db_url")
        ctx.update({"testDb": db_url})
        logger.info(f"💾 Test DB provisioned: {db_url}")

    def _notify_parent_success(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Notifies the parent CI/CD pipeline machine that integration tests passed.

        Args:
            interpreter (Interpreter): The state machine interpreter of the integration tester.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this action.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        if interpreter.parent:
            asyncio.create_task(interpreter.parent.send("TESTS_PASSED"))
            logger.info("📢 Notified parent: TESTS_PASSED")
        else:
            logger.warning(
                "⚠️ Integration tester has no parent to notify success."
            )

    def _notify_parent_failure(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Notifies the parent CI/CD pipeline machine that integration tests failed.

        Args:
            interpreter (Interpreter): The state machine interpreter of the integration tester.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this action.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        if interpreter.parent:
            error_msg = ctx.get("error", "Unknown integration test failure")
            asyncio.create_task(
                interpreter.parent.send("TESTS_FAILED", error=error_msg)
            )
            logger.error(
                f"📢 Notified parent: TESTS_FAILED (Error: {error_msg})"
            )
        else:
            logger.warning(
                "⚠️ Integration tester has no parent to notify failure."
            )


class PipelineLogic(MachineLogic):
    """
    Encapsulates custom logic (actions, services, guards) for the main CI/CD Pipeline state machine.

    This class provides the implementation for various pipeline stages like
    setting up, building, testing, and deploying, and coordinates with
    child actors where necessary.
    """

    def __init__(self, integration_tester_machine: Any):
        """
        Initializes the PipelineLogic with the integration tester machine definition.

        Args:
            integration_tester_machine (Any): The pre-created machine definition
                                              for the integration tester actor, which
                                              will be invoked as a service.
        """
        super().__init__()
        self._integration_tester_machine = integration_tester_machine
        self._setup_actions()
        self._setup_services()
        # No guards for this example, but they would be set up here

    def _setup_actions(self) -> None:
        """
        Defines and sets up all action functions used by the main pipeline machine.

        Actions are side effects performed during state transitions or on entry/exit of states.
        Each action receives the interpreter, context, event, and action definition.
        """
        self.actions = {
            "setCommitId": self._set_commit_id,
            "logError": self._log_error,
            "setArtifactUrl": self._set_artifact_url,
            "spawn_integrationTester": self._spawn_integration_tester,
        }

    def _setup_services(self) -> None:
        """
        Defines and sets up all service functions used by the main pipeline machine.

        Services are asynchronous operations invoked by states. They can be
        other state machines (actors) or external async functions.
        """
        self.services = {
            # Build steps services
            "setupWorkspace": lambda i, c, e: async_task(
                "Setup Workspace", 1, 0.05
            ),
            "installDependencies": lambda i, c, e: async_task(
                "Install Dependencies", 2, 0.05
            ),
            "compileCode": lambda i, c, e: async_task("Compile Code", 3, 0.05),
            "packageArtifacts": lambda i, c, e: async_task(  # ✅ FIXED: Passing result_data correctly
                "Package Artifacts",
                1.5,
                0.05,
                result_data={
                    "url": f"http://artifacts.dev/build-{c['commitId']}.tar.gz"
                },
            ),
            # Quality checks services
            "runLinter": lambda i, c, e: async_task("Run Linter", 2.5, 0.05),
            "runUnitTests": lambda i, c, e: async_task(
                "Run Unit Tests", 4, 0.05
            ),
            # Deployment services
            "deployToStaging": lambda i, c, e: async_task(
                "Deploy to Staging", 5, 0.05
            ),
            "runSmokeTests": lambda i, c, e: async_task(
                "Run Smoke Tests", 2, 0.05
            ),
            # This special service provides the machine definition for the actor to be spawned.
            "integrationTester": self._integration_tester_machine,
        }

    # --- Actions ---
    def _set_commit_id(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Sets the commit ID in the pipeline's context upon receiving a COMMIT_PUSHED event.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event containing the 'commitId' payload.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        commit_id = evt.payload.get("commitId")
        ctx.update({"commitId": commit_id})
        logger.info(f"⚙️ Pipeline started for commit: {commit_id}")

    def _log_error(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Logs an error message and updates the pipeline's context with the error details.

        This action is typically triggered when an invoked service fails (`onError`).

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event containing error data from the failed service.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        error_data = evt.data
        ctx.update({"error": str(error_data)})
        logger.error(f"❌ Pipeline error: {error_data}")

    def _set_artifact_url(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Sets the artifact URL in the pipeline's context after packaging.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event containing the 'url' data from the packaging service.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        artifact_url = evt.data.get("url")
        ctx.update({"artifactUrl": artifact_url})
        logger.info(f"📦 Artifact packaged: {artifact_url}")

    def _spawn_integration_tester(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Logs the intent to spawn the integration tester actor.

        Note: The actual spawning of the actor is handled automatically by the
        `xstate-machine` library when an `invoke` configuration points to a
        service that is a machine definition. This action serves as a log point
        or to add any pre-spawn setup logic if needed.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this action.
            action_def (Any): The action definition (unused here, but required by signature).
        """
        logger.info("👶 Attempting to spawn integrationTester actor...")


# -----------------------------------------------------------------------------
# Main Simulation Execution
# -----------------------------------------------------------------------------


async def main() -> None:
    """
    Configures and runs a complex simulation of a CI/CD pipeline state machine,
    showcasing parallel states, invoked async services, and spawned actors.
    """
    logger.info("🎬 --- CI/CD Pipeline Simulation --- 🎬\n")

    # -------------------------------------------------------------------------
    # 1. Define and Create the Nested Machine (Actor) for Integration Tests
    # -------------------------------------------------------------------------
    integration_test_config = get_integration_test_config()
    integration_test_logic = IntegrationTestLogic()
    # Create the machine definition for the actor, which will be passed to the parent's logic
    integration_tester_machine = create_machine(
        integration_test_config, integration_test_logic
    )

    # -------------------------------------------------------------------------
    # 2. Define and Create the Main CI/CD Pipeline Machine
    # -------------------------------------------------------------------------
    pipeline_config = get_pipeline_config()
    # Pass the created integration tester machine definition to the pipeline's logic
    pipeline_logic = PipelineLogic(integration_tester_machine)
    pipeline_machine = create_machine(pipeline_config, pipeline_logic)

    # -------------------------------------------------------------------------
    # 3. Create and Run the Simulation Interpreter
    # -------------------------------------------------------------------------
    interpreter = Interpreter(pipeline_machine)
    interpreter.use(
        LoggingInspector()
    )  # 🕵️‍♂️ Enable detailed state transition logging
    await interpreter.start()

    logger.info("\n--- 🤖 SIMULATION LOG ---")
    logger.info(f"Initial State: {interpreter.current_state_ids}\n")

    # Kick off the pipeline with a new commit.
    commit_id = f"commit-{uuid4().hex[:7]}"
    logger.info(f"➡️ Sending COMMIT_PUSHED event for commit: {commit_id}...")
    await interpreter.send("COMMIT_PUSHED", commitId=commit_id)

    # Let the simulation run to completion. A real application would not have
    # this fixed sleep; it would react to events as they come in over its entire lifecycle,
    # or wait for the machine to reach a final state.
    # Note: Current time is included for debugging asynchronous timing.
    logger.info(
        f"⏳ Allowing the pipeline to run for 25 seconds... (Current time: {asyncio.current_task()._loop.time():.2f}s)"
    )
    await asyncio.sleep(25)

    logger.info("\n--- 🏁 SIMULATION COMPLETE ---")
    logger.info(f"Final State: {interpreter.current_state_ids}")
    logger.info(f"Final Context: {interpreter.context}")

    # Cleanly shut down the interpreter and any actors it spawned.
    await interpreter.stop()
    logger.info("Interpreter stopped.")


if __name__ == "__main__":
    asyncio.run(main())
