"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    download_manager.json
Template:  pythonic-class
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template download_manager.json --template pythonic-class

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""

import logging
from typing import Any, Dict, Union

from xstate_statemachine import (
    Interpreter,
    State,
    StateMachine,
    SyncInterpreter,
    action,
    guard,
    service,
)

logger = logging.getLogger(__name__)


class DownloadManagerMachine(StateMachine):
    """DownloadManager state machine using the declarative class-based API."""

    machine_id = "downloadManager"
    initial_context = {"progress": 0, "retries": 0}

    idle = State(
        "idle",
        initial=True,
        on={"START": {"target": "downloading", "actions": ["resetProgress"]}},
    )
    downloading = State(
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
    paused = State(
        "paused", on={"RESUME": "downloading", "CANCEL": "idle"}, tags=["busy"]
    )
    failed = State(
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
    complete = State("complete", final=True)

    # Actions
    @action
    def count_retry(
        self,
        interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Execute the ``countRetry`` action.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this action.
            action_def: Metadata about the action being executed.
        """
        try:
            logger.info("Executing action: countRetry")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'countRetry' failed")
            raise

    @action
    def log_start(
        self,
        interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Execute the ``logStart`` action.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this action.
            action_def: Metadata about the action being executed.
        """
        try:
            logger.info("Executing action: logStart")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'logStart' failed")
            raise

    @action
    def log_timeout(
        self,
        interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Execute the ``logTimeout`` action.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this action.
            action_def: Metadata about the action being executed.
        """
        try:
            logger.info("Executing action: logTimeout")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'logTimeout' failed")
            raise

    @action
    def reset_progress(
        self,
        interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Execute the ``resetProgress`` action.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this action.
            action_def: Metadata about the action being executed.
        """
        try:
            logger.info("Executing action: resetProgress")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'resetProgress' failed")
            raise

    @action
    def save_file(
        self,
        interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Execute the ``saveFile`` action.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this action.
            action_def: Metadata about the action being executed.
        """
        try:
            logger.info("Executing action: saveFile")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'saveFile' failed")
            raise

    # Guards
    @guard
    def can_retry(
        self,
        context: Dict[str, Any],
        event: Any,
    ) -> bool:
        """
        Evaluate the ``canRetry`` guard.

        Args:
            context: Current machine context dictionary.
            event: The event being evaluated.
        """
        logger.info("Evaluating guard: canRetry")
        # TODO: implement guard logic
        return True

    # Services
    @service
    def fetch_file(
        self,
        interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
        context: Dict[str, Any],
        event: Any,
    ) -> Dict[str, Any]:
        """
        Run the ``fetchFile`` service.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this service.
        """
        try:
            logger.info("Running service: fetchFile")
            # TODO: implement service logic
            return {"result": "done"}
        except Exception:
            logger.exception("Service 'fetchFile' failed")
            raise
