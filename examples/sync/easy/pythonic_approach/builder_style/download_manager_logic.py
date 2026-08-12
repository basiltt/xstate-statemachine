"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    download_manager.json
Template:  pythonic-builder
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template download_manager.json --template pythonic-builder

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""

import logging
from typing import Any, Dict

from xstate_statemachine import (
    MachineBuilder,
    SyncInterpreter,
    action,
    guard,
    service,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------


@action
def count_retry(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``countRetry`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: countRetry")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'countRetry' failed")
        raise


@action
def log_start(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``logStart`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: logStart")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'logStart' failed")
        raise


@action
def log_timeout(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``logTimeout`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: logTimeout")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'logTimeout' failed")
        raise


@action
def reset_progress(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``resetProgress`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: resetProgress")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'resetProgress' failed")
        raise


@action
def save_file(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``saveFile`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: saveFile")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'saveFile' failed")
        raise


# -----------------------------------------------------------------------
# Guards
# -----------------------------------------------------------------------


@guard
def can_retry(
    context: Dict[str, Any],
    event: Any,
) -> bool:
    """Evaluate the ``canRetry`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard: canRetry")
    # TODO: implement guard logic
    return True


# -----------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------


@service
def fetch_file(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
) -> Dict[str, Any]:
    """Run the ``fetchFile`` service.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this service.
    """
    logger.info("Running service: fetchFile")
    try:
        # TODO: implement service logic
        return {"result": "done"}
    except Exception:
        logger.exception("Service 'fetchFile' failed")
        raise


def build() -> Any:
    """Build the downloadManager machine (builder style)."""
    builder = MachineBuilder("downloadManager")
    builder.context({"progress": 0, "retries": 0})
    builder.state(
        "idle",
        initial=True,
        on={"START": {"target": "downloading", "actions": ["resetProgress"]}},
    )
    builder.state(
        "downloading",
        entry=["logStart"],
        on={"PAUSE": "paused", "CANCEL": "idle"},
        after={30000: {"target": "failed", "actions": ["logTimeout"]}},
        invoke={
            "src": "fetchFile",
            "id": "fetch",
            "onDone": {"target": "complete", "actions": ["saveFile"]},
            "onError": "failed",
        },
        tags=["busy"],
    )
    builder.state(
        "paused", on={"RESUME": "downloading", "CANCEL": "idle"}, tags=["busy"]
    )
    builder.state(
        "failed",
        on={
            "RETRY": {
                "target": "downloading",
                "guard": "canRetry",
                "actions": ["countRetry"],
            }
        },
        meta={"alert": True},
    )
    builder.state("complete", final=True)
    builder.action("countRetry", count_retry)
    builder.action("logStart", log_start)
    builder.action("logTimeout", log_timeout)
    builder.action("resetProgress", reset_progress)
    builder.action("saveFile", save_file)
    builder.guard("canRetry", can_retry)
    builder.service("fetchFile", fetch_file)
    return builder.build()
