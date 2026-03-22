# tests/tests_cli/test_stress_50machines.py
# ---------------------------------------------------------------------------
# Stress test: 50 real-world-inspired XState machine configs x 5 templates
# = 250 code generation runs.  Each must py_compile + importlib import OK.
# ---------------------------------------------------------------------------
"""Stress-test the CLI code generator with 50 complex, real-world-inspired
XState machine configurations across all five template strategies.

Each generated file is validated by:
  1. ``py_compile.compile()`` -- syntactically valid Python
  2. ``importlib`` import     -- loadable without runtime errors
"""

from __future__ import annotations

import importlib
import importlib.util
import py_compile
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from xstate_statemachine.cli.extractor import extract_logic_names
from xstate_statemachine.cli.strategies import GenerationContext, get_strategy
from xstate_statemachine.cli.utils import camel_to_snake

# ---------------------------------------------------------------------------
# Template list
# ---------------------------------------------------------------------------
TEMPLATES: List[str] = [
    "class-json",
    "function-json",
    "pythonic-class",
    "pythonic-builder",
    "pythonic-functional",
]

# ---------------------------------------------------------------------------
# 50 Machine Configurations
# ---------------------------------------------------------------------------
MACHINES: Dict[str, Dict[str, Any]] = {
    # ===================================================================
    # A. Simple / Flat Machines  (4)
    # ===================================================================
    "toggleSwitch": {
        "id": "toggleSwitch",
        "initial": "off",
        "states": {
            "off": {"on": {"TOGGLE": "on"}},
            "on": {"on": {"TOGGLE": "off"}},
        },
    },
    "trafficLight": {
        "id": "trafficLight",
        "initial": "red",
        "states": {
            "red": {"on": {"NEXT": "green"}},
            "green": {"on": {"NEXT": "yellow"}},
            "yellow": {"on": {"NEXT": "red"}},
        },
    },
    "doorLock": {
        "id": "doorLock",
        "initial": "locked",
        "states": {
            "locked": {
                "entry": "logLocked",
                "exit": "clearAlarm",
                "on": {"UNLOCK": "unlocked"},
            },
            "unlocked": {
                "entry": "logUnlocked",
                "on": {"LOCK": "locked", "OPEN": "opened"},
            },
            "opened": {
                "exit": "closeDoor",
                "on": {"CLOSE": "unlocked"},
            },
        },
    },
    "emptyMachine": {
        "id": "emptyMachine",
        "initial": "idle",
        "states": {"idle": {}},
    },
    # ===================================================================
    # B. Nested / Hierarchical Machines  (9)
    # ===================================================================
    "nestedAuth": {
        "id": "nestedAuth",
        "initial": "unauthenticated",
        "states": {
            "unauthenticated": {"on": {"LOGIN": "authenticating"}},
            "authenticating": {
                "initial": "enteringCredentials",
                "states": {
                    "enteringCredentials": {
                        "on": {"SUBMIT": "verifying"},
                    },
                    "verifying": {
                        "on": {
                            "SUCCESS": "#nestedAuth.authenticated",
                            "FAILURE": "enteringCredentials",
                        },
                    },
                },
                "on": {"CANCEL": "unauthenticated"},
            },
            "authenticated": {"on": {"LOGOUT": "unauthenticated"}},
        },
    },
    "deepNesting": {
        "id": "deepNesting",
        "initial": "level1",
        "states": {
            "level1": {
                "initial": "level2",
                "states": {
                    "level2": {
                        "initial": "level3",
                        "states": {
                            "level3": {
                                "on": {"GO_UP": "#deepNesting.done"},
                            },
                        },
                    },
                },
            },
            "done": {"type": "final"},
        },
    },
    "nestedWithActions": {
        "id": "nestedWithActions",
        "initial": "parent",
        "states": {
            "parent": {
                "initial": "childA",
                "entry": "enterParent",
                "exit": "exitParent",
                "states": {
                    "childA": {
                        "entry": "enterChildA",
                        "exit": "exitChildA",
                        "on": {"NEXT": "childB"},
                    },
                    "childB": {
                        "entry": ["enterChildB", "logTransition"],
                        "on": {"DONE": "#nestedWithActions.finished"},
                    },
                },
            },
            "finished": {"type": "final"},
        },
    },
    "nestedWithGuards": {
        "id": "nestedWithGuards",
        "initial": "outer",
        "states": {
            "outer": {
                "initial": "inner1",
                "states": {
                    "inner1": {
                        "on": {
                            "PROCEED": {
                                "target": "inner2",
                                "guard": "isReady",
                            },
                        },
                    },
                    "inner2": {
                        "on": {
                            "FINISH": {
                                "target": "#nestedWithGuards.complete",
                                "guard": "isValid",
                            },
                        },
                    },
                },
            },
            "complete": {"type": "final"},
        },
    },
    "nestedWithInvoke": {
        "id": "nestedWithInvoke",
        "initial": "idle",
        "states": {
            "idle": {"on": {"START": "processing"}},
            "processing": {
                "initial": "fetching",
                "states": {
                    "fetching": {
                        "invoke": {
                            "src": "fetchData",
                            "onDone": "transforming",
                            "onError": "#nestedWithInvoke.error",
                        },
                    },
                    "transforming": {
                        "invoke": {
                            "src": "transformData",
                            "onDone": "#nestedWithInvoke.done",
                            "onError": "#nestedWithInvoke.error",
                        },
                    },
                },
            },
            "done": {"type": "final"},
            "error": {"on": {"RETRY": "processing"}},
        },
    },
    "nestedWithAfter": {
        "id": "nestedWithAfter",
        "initial": "active",
        "states": {
            "active": {
                "initial": "step1",
                "states": {
                    "step1": {
                        "after": {"2000": "step2"},
                    },
                    "step2": {
                        "after": {
                            "3000": "#nestedWithAfter.timeout",
                        },
                        "on": {"COMPLETE": "#nestedWithAfter.done"},
                    },
                },
            },
            "done": {"type": "final"},
            "timeout": {"on": {"RETRY": "active"}},
        },
    },
    "multipleNested": {
        "id": "multipleNested",
        "initial": "main",
        "states": {
            "main": {
                "initial": "sectionA",
                "states": {
                    "sectionA": {
                        "initial": "a1",
                        "states": {
                            "a1": {"on": {"NEXT_A": "a2"}},
                            "a2": {
                                "on": {
                                    "TO_B": "#multipleNested.main.sectionB",
                                },
                            },
                        },
                    },
                    "sectionB": {
                        "initial": "b1",
                        "states": {
                            "b1": {"on": {"NEXT_B": "b2"}},
                            "b2": {
                                "on": {
                                    "TO_C": "#multipleNested.main.sectionC",
                                },
                            },
                        },
                    },
                    "sectionC": {
                        "initial": "c1",
                        "states": {
                            "c1": {"on": {"FINISH": "#multipleNested.done"}},
                        },
                    },
                },
            },
            "done": {"type": "final"},
        },
    },
    "nestedFinalStates": {
        "id": "nestedFinalStates",
        "initial": "workflow",
        "states": {
            "workflow": {
                "initial": "step1",
                "states": {
                    "step1": {"on": {"NEXT": "step2"}},
                    "step2": {"on": {"NEXT": "step3"}},
                    "step3": {"on": {"COMPLETE": "completed"}},
                    "completed": {"type": "final"},
                },
                "onDone": "allDone",
            },
            "allDone": {"type": "final"},
        },
    },
    "nestedMixedFeatures": {
        "id": "nestedMixedFeatures",
        "initial": "phase1",
        "states": {
            "phase1": {
                "initial": "init",
                "entry": "logPhase1",
                "states": {
                    "init": {
                        "invoke": {
                            "src": "loadConfig",
                            "onDone": "ready",
                            "onError": "#nestedMixedFeatures.failed",
                        },
                    },
                    "ready": {
                        "on": {
                            "PROCEED": {
                                "target": "#nestedMixedFeatures.phase2",
                                "guard": "configValid",
                                "actions": "logProceed",
                            },
                        },
                        "after": {"5000": "#nestedMixedFeatures.failed"},
                    },
                },
            },
            "phase2": {
                "entry": "startPhase2",
                "exit": "cleanupPhase2",
                "on": {
                    "FINISH": {
                        "target": "done",
                        "actions": ["saveResults", "notifyComplete"],
                    },
                },
            },
            "done": {"type": "final"},
            "failed": {"on": {"RETRY": "phase1"}},
        },
    },
    # ===================================================================
    # C. Parallel State Machines  (6)
    # ===================================================================
    "parallelSimple": {
        "id": "parallelSimple",
        "initial": "active",
        "states": {
            "active": {
                "type": "parallel",
                "states": {
                    "upload": {
                        "initial": "idle",
                        "states": {
                            "idle": {"on": {"START_UPLOAD": "uploading"}},
                            "uploading": {"on": {"UPLOAD_DONE": "idle"}},
                        },
                    },
                    "download": {
                        "initial": "idle",
                        "states": {
                            "idle": {
                                "on": {"START_DOWNLOAD": "downloading"},
                            },
                            "downloading": {
                                "on": {"DOWNLOAD_DONE": "idle"},
                            },
                        },
                    },
                },
            },
        },
    },
    "parallelWithActions": {
        "id": "parallelWithActions",
        "initial": "running",
        "states": {
            "running": {
                "type": "parallel",
                "states": {
                    "audio": {
                        "initial": "muted",
                        "states": {
                            "muted": {
                                "entry": "muteAudio",
                                "on": {"UNMUTE": "playing"},
                            },
                            "playing": {
                                "entry": "playAudio",
                                "exit": "stopAudio",
                                "on": {"MUTE": "muted"},
                            },
                        },
                    },
                    "video": {
                        "initial": "hidden",
                        "states": {
                            "hidden": {
                                "entry": "hideVideo",
                                "on": {"SHOW": "visible"},
                            },
                            "visible": {
                                "entry": "showVideo",
                                "exit": "hideVideo",
                                "on": {"HIDE": "hidden"},
                            },
                        },
                    },
                },
            },
        },
    },
    "parallelWithGuards": {
        "id": "parallelWithGuards",
        "initial": "dashboard",
        "states": {
            "dashboard": {
                "type": "parallel",
                "states": {
                    "notifications": {
                        "initial": "disabled",
                        "states": {
                            "disabled": {
                                "on": {
                                    "ENABLE_NOTIF": {
                                        "target": "enabled",
                                        "guard": "hasPermission",
                                    },
                                },
                            },
                            "enabled": {
                                "on": {"DISABLE_NOTIF": "disabled"},
                            },
                        },
                    },
                    "theme": {
                        "initial": "light",
                        "states": {
                            "light": {
                                "on": {
                                    "TOGGLE_THEME": {
                                        "target": "dark",
                                        "guard": "prefersReducedMotion",
                                    },
                                },
                            },
                            "dark": {"on": {"TOGGLE_THEME": "light"}},
                        },
                    },
                },
            },
        },
    },
    "parallelNested": {
        "id": "parallelNested",
        "initial": "app",
        "states": {
            "app": {
                "type": "parallel",
                "states": {
                    "auth": {
                        "initial": "loggedOut",
                        "states": {
                            "loggedOut": {
                                "on": {"LOGIN": "loggingIn"},
                            },
                            "loggingIn": {
                                "initial": "entering",
                                "states": {
                                    "entering": {
                                        "on": {"SUBMIT": "validating"},
                                    },
                                    "validating": {
                                        "on": {
                                            "OK": "#parallelNested.app.auth.loggedIn",
                                            "FAIL": "entering",
                                        },
                                    },
                                },
                            },
                            "loggedIn": {
                                "on": {"LOGOUT": "loggedOut"},
                            },
                        },
                    },
                    "sidebar": {
                        "initial": "collapsed",
                        "states": {
                            "collapsed": {
                                "on": {"EXPAND": "expanded"},
                            },
                            "expanded": {
                                "on": {"COLLAPSE": "collapsed"},
                            },
                        },
                    },
                },
            },
        },
    },
    "parallelWithInvoke": {
        "id": "parallelWithInvoke",
        "initial": "active",
        "states": {
            "active": {
                "type": "parallel",
                "states": {
                    "data": {
                        "initial": "loading",
                        "states": {
                            "loading": {
                                "invoke": {
                                    "src": "fetchUserData",
                                    "onDone": "loaded",
                                    "onError": "error",
                                },
                            },
                            "loaded": {
                                "on": {"REFRESH": "loading"},
                            },
                            "error": {"on": {"RETRY": "loading"}},
                        },
                    },
                    "ui": {
                        "initial": "normal",
                        "states": {
                            "normal": {
                                "on": {"FULLSCREEN": "fullscreen"},
                            },
                            "fullscreen": {
                                "on": {"EXIT_FULLSCREEN": "normal"},
                            },
                        },
                    },
                },
            },
        },
    },
    "parallelComplex": {
        "id": "parallelComplex",
        "initial": "workspace",
        "states": {
            "workspace": {
                "type": "parallel",
                "states": {
                    "editor": {
                        "initial": "idle",
                        "states": {
                            "idle": {
                                "on": {"EDIT": "editing"},
                                "entry": "clearEditor",
                            },
                            "editing": {
                                "on": {
                                    "SAVE": {
                                        "target": "saving",
                                        "guard": "hasChanges",
                                        "actions": "preparePayload",
                                    },
                                },
                            },
                            "saving": {
                                "invoke": {
                                    "src": "saveDocument",
                                    "onDone": "idle",
                                    "onError": "editing",
                                },
                            },
                        },
                    },
                    "chat": {
                        "initial": "disconnected",
                        "states": {
                            "disconnected": {
                                "on": {"CONNECT": "connecting"},
                            },
                            "connecting": {
                                "invoke": {
                                    "src": "connectChat",
                                    "onDone": "connected",
                                    "onError": "disconnected",
                                },
                            },
                            "connected": {
                                "entry": "showChatPanel",
                                "on": {"DISCONNECT": "disconnected"},
                            },
                        },
                    },
                    "presence": {
                        "initial": "online",
                        "states": {
                            "online": {
                                "after": {"300000": "away"},
                                "on": {"SET_AWAY": "away"},
                            },
                            "away": {
                                "on": {"SET_ONLINE": "online"},
                            },
                        },
                    },
                },
            },
        },
    },
    # ===================================================================
    # D. Complex Context Machines  (6)
    # ===================================================================
    "simpleContext": {
        "id": "simpleContext",
        "initial": "idle",
        "context": {"count": 0},
        "states": {
            "idle": {
                "on": {
                    "INCREMENT": {
                        "target": "idle",
                        "actions": "incrementCount",
                    },
                },
            },
        },
    },
    "nestedContext": {
        "id": "nestedContext",
        "initial": "idle",
        "context": {
            "user": {"name": "", "role": "guest", "loggedIn": False},
            "settings": {"theme": "light", "lang": "en"},
        },
        "states": {
            "idle": {
                "on": {"LOGIN": {"target": "active", "actions": "setUser"}},
            },
            "active": {
                "on": {
                    "LOGOUT": {
                        "target": "idle",
                        "actions": "clearUser",
                    },
                },
            },
        },
    },
    "arrayContext": {
        "id": "arrayContext",
        "initial": "shopping",
        "context": {"items": [], "history": [], "total": 0},
        "states": {
            "shopping": {
                "on": {
                    "ADD_ITEM": {
                        "target": "shopping",
                        "actions": "addItem",
                    },
                    "CHECKOUT": {
                        "target": "checkout",
                        "guard": "hasItems",
                    },
                },
            },
            "checkout": {
                "on": {
                    "CONFIRM": {
                        "target": "confirmed",
                        "actions": "processOrder",
                    },
                },
            },
            "confirmed": {"type": "final"},
        },
    },
    "mixedTypeContext": {
        "id": "mixedTypeContext",
        "initial": "idle",
        "context": {
            "name": "default",
            "count": 42,
            "ratio": 3.14,
            "active": True,
            "nullable": None,
            "tags": ["alpha", "beta"],
            "metadata": {"version": 1, "debug": False},
        },
        "states": {
            "idle": {"on": {"START": "running"}},
            "running": {"on": {"STOP": "idle"}},
        },
    },
    "largeContext": {
        "id": "largeContext",
        "initial": "idle",
        "context": {
            "field1": "",
            "field2": 0,
            "field3": False,
            "field4": [],
            "field5": None,
            "field6": "hello",
            "field7": 99,
            "field8": True,
            "field9": [1, 2, 3],
            "field10": {"a": 1},
            "field11": "world",
            "field12": 0.5,
            "field13": False,
            "field14": [],
            "field15": None,
            "field16": "extra",
        },
        "states": {
            "idle": {
                "on": {"PROCESS": "processing"},
            },
            "processing": {
                "on": {"DONE": "idle"},
            },
        },
    },
    "contextWithActions": {
        "id": "contextWithActions",
        "initial": "idle",
        "context": {"retries": 0, "lastError": None, "data": None},
        "states": {
            "idle": {
                "on": {
                    "FETCH": {
                        "target": "loading",
                        "actions": "resetRetries",
                    },
                },
            },
            "loading": {
                "invoke": {
                    "src": "fetchService",
                    "onDone": {
                        "target": "success",
                        "actions": "setData",
                    },
                    "onError": {
                        "target": "error",
                        "actions": "setError",
                    },
                },
            },
            "success": {
                "on": {"REFRESH": "loading"},
            },
            "error": {
                "on": {
                    "RETRY": {
                        "target": "loading",
                        "guard": "canRetry",
                        "actions": "incrementRetries",
                    },
                },
            },
        },
    },
    # ===================================================================
    # E. Guard-Heavy Machines  (5)
    # ===================================================================
    "guardedTransitions": {
        "id": "guardedTransitions",
        "initial": "idle",
        "states": {
            "idle": {
                "on": {
                    "START": {
                        "target": "running",
                        "guard": "isReady",
                    },
                },
            },
            "running": {
                "on": {
                    "PAUSE": {
                        "target": "paused",
                        "guard": "canPause",
                    },
                    "STOP": {
                        "target": "stopped",
                        "guard": "canStop",
                    },
                },
            },
            "paused": {
                "on": {
                    "RESUME": {
                        "target": "running",
                        "guard": "canResume",
                    },
                },
            },
            "stopped": {"type": "final"},
        },
    },
    "condKeyGuards": {
        "id": "condKeyGuards",
        "initial": "draft",
        "states": {
            "draft": {
                "on": {
                    "SUBMIT": {
                        "target": "review",
                        "cond": "isComplete",
                    },
                },
            },
            "review": {
                "on": {
                    "APPROVE": {
                        "target": "approved",
                        "cond": "isAuthorized",
                    },
                    "REJECT": {
                        "target": "draft",
                        "cond": "hasPermission",
                    },
                },
            },
            "approved": {"type": "final"},
        },
    },
    "multiGuardedTarget": {
        "id": "multiGuardedTarget",
        "initial": "pending",
        "states": {
            "pending": {
                "on": {
                    "EVALUATE": [
                        {
                            "target": "approved",
                            "guard": "scoreAbove90",
                        },
                        {
                            "target": "review",
                            "guard": "scoreAbove50",
                        },
                        {"target": "rejected"},
                    ],
                },
            },
            "approved": {"type": "final"},
            "review": {"on": {"DECIDE": "approved"}},
            "rejected": {"type": "final"},
        },
    },
    "mixedGuardStyles": {
        "id": "mixedGuardStyles",
        "initial": "start",
        "states": {
            "start": {
                "on": {
                    "GO_A": {
                        "target": "stateA",
                        "guard": "checkA",
                    },
                    "GO_B": {
                        "target": "stateB",
                        "cond": "checkB",
                    },
                },
            },
            "stateA": {
                "on": {
                    "TO_C": {
                        "target": "stateC",
                        "cond": "checkC",
                    },
                },
            },
            "stateB": {
                "on": {
                    "TO_C": {
                        "target": "stateC",
                        "guard": "checkD",
                    },
                },
            },
            "stateC": {"type": "final"},
        },
    },
    "guardsWithActions": {
        "id": "guardsWithActions",
        "initial": "idle",
        "states": {
            "idle": {
                "on": {
                    "SUBMIT": {
                        "target": "validating",
                        "guard": "formValid",
                        "actions": "captureFormData",
                    },
                },
            },
            "validating": {
                "on": {
                    "PASS": {
                        "target": "submitting",
                        "guard": "dataClean",
                        "actions": ["sanitize", "logValidation"],
                    },
                    "FAIL": {
                        "target": "idle",
                        "actions": "showErrors",
                    },
                },
            },
            "submitting": {
                "invoke": {
                    "src": "submitForm",
                    "onDone": "success",
                    "onError": "idle",
                },
            },
            "success": {"type": "final"},
        },
    },
    # ===================================================================
    # F. Invoke / Services Machines  (6)
    # ===================================================================
    "singleInvoke": {
        "id": "singleInvoke",
        "initial": "idle",
        "states": {
            "idle": {"on": {"FETCH": "loading"}},
            "loading": {
                "invoke": {
                    "src": "fetchUser",
                    "onDone": "loaded",
                },
            },
            "loaded": {"on": {"REFRESH": "loading"}},
        },
    },
    "invokeWithError": {
        "id": "invokeWithError",
        "initial": "idle",
        "states": {
            "idle": {"on": {"FETCH": "loading"}},
            "loading": {
                "invoke": {
                    "src": "fetchData",
                    "onDone": "success",
                    "onError": "failure",
                },
            },
            "success": {"on": {"RESET": "idle"}},
            "failure": {"on": {"RETRY": "loading"}},
        },
    },
    "multipleInvokes": {
        "id": "multipleInvokes",
        "initial": "idle",
        "states": {
            "idle": {"on": {"LOAD": "loading"}},
            "loading": {
                "invoke": [
                    {
                        "src": "fetchProfile",
                        "onDone": "ready",
                        "onError": "error",
                    },
                    {
                        "src": "fetchSettings",
                        "onDone": "ready",
                        "onError": "error",
                    },
                ],
            },
            "ready": {"on": {"RELOAD": "loading"}},
            "error": {"on": {"RETRY": "loading"}},
        },
    },
    "invokeWithActions": {
        "id": "invokeWithActions",
        "initial": "idle",
        "states": {
            "idle": {"on": {"START": "processing"}},
            "processing": {
                "invoke": {
                    "src": "processTask",
                    "onDone": {
                        "target": "complete",
                        "actions": ["saveResult", "notifySuccess"],
                    },
                    "onError": {
                        "target": "failed",
                        "actions": ["logError", "notifyFailure"],
                    },
                },
            },
            "complete": {"on": {"RESTART": "idle"}},
            "failed": {"on": {"RETRY": "processing"}},
        },
    },
    "invokeWithGuards": {
        "id": "invokeWithGuards",
        "initial": "idle",
        "states": {
            "idle": {"on": {"START": "loading"}},
            "loading": {
                "invoke": {
                    "src": "validateAndLoad",
                    "onDone": [
                        {
                            "target": "premium",
                            "guard": "isPremiumUser",
                        },
                        {"target": "basic"},
                    ],
                    "onError": "error",
                },
            },
            "premium": {"on": {"LOGOUT": "idle"}},
            "basic": {"on": {"LOGOUT": "idle"}},
            "error": {"on": {"RETRY": "loading"}},
        },
    },
    "chainedInvokes": {
        "id": "chainedInvokes",
        "initial": "step1",
        "states": {
            "step1": {
                "invoke": {
                    "src": "fetchRawData",
                    "onDone": "step2",
                    "onError": "failed",
                },
            },
            "step2": {
                "invoke": {
                    "src": "transformData",
                    "onDone": "step3",
                    "onError": "failed",
                },
            },
            "step3": {
                "invoke": {
                    "src": "persistData",
                    "onDone": "complete",
                    "onError": "failed",
                },
            },
            "complete": {"type": "final"},
            "failed": {"on": {"RETRY": "step1"}},
        },
    },
    # ===================================================================
    # G. Delayed Transitions (`after`)  (5)
    # ===================================================================
    "simpleAfter": {
        "id": "simpleAfter",
        "initial": "waiting",
        "states": {
            "waiting": {"after": {"3000": "timeout"}},
            "timeout": {"on": {"RESET": "waiting"}},
        },
    },
    "afterWithActions": {
        "id": "afterWithActions",
        "initial": "active",
        "states": {
            "active": {
                "after": {
                    "5000": {
                        "target": "expired",
                        "actions": "logTimeout",
                    },
                },
                "on": {"RENEW": "active"},
            },
            "expired": {
                "entry": "notifyExpiry",
                "on": {"RESTART": "active"},
            },
        },
    },
    "afterWithGuard": {
        "id": "afterWithGuard",
        "initial": "countdown",
        "states": {
            "countdown": {
                "after": {
                    "1000": [
                        {
                            "target": "launched",
                            "guard": "allSystemsGo",
                        },
                        {"target": "aborted"},
                    ],
                },
            },
            "launched": {"type": "final"},
            "aborted": {"on": {"RETRY": "countdown"}},
        },
    },
    "multipleAfters": {
        "id": "multipleAfters",
        "initial": "idle",
        "states": {
            "idle": {"on": {"ACTIVATE": "active"}},
            "active": {
                "after": {
                    "1000": {
                        "target": "warning",
                        "actions": "logWarning",
                    },
                },
                "on": {"DEACTIVATE": "idle"},
            },
            "warning": {
                "after": {
                    "2000": {
                        "target": "critical",
                        "actions": "logCritical",
                    },
                },
                "on": {"ACKNOWLEDGE": "active"},
            },
            "critical": {
                "after": {"3000": "shutdown"},
                "on": {"RESOLVE": "active"},
            },
            "shutdown": {"type": "final"},
        },
    },
    "afterInNestedState": {
        "id": "afterInNestedState",
        "initial": "session",
        "states": {
            "session": {
                "initial": "active",
                "states": {
                    "active": {
                        "after": {"600000": "warning"},
                        "on": {"ACTIVITY": "active"},
                    },
                    "warning": {
                        "after": {
                            "60000": "#afterInNestedState.expired",
                        },
                        "on": {"ACTIVITY": "active"},
                    },
                },
            },
            "expired": {
                "entry": "forceLogout",
                "on": {"RE_LOGIN": "session"},
            },
        },
    },
    # ===================================================================
    # H. Large Scale Machines  (5)
    # ===================================================================
    "tenStateLinear": {
        "id": "tenStateLinear",
        "initial": "s1",
        "states": {
            "s1": {"on": {"E1": "s2"}},
            "s2": {"on": {"E2": "s3"}},
            "s3": {"on": {"E3": "s4"}},
            "s4": {"on": {"E4": "s5"}},
            "s5": {"on": {"E5": "s6"}},
            "s6": {"on": {"E6": "s7"}},
            "s7": {"on": {"E7": "s8"}},
            "s8": {"on": {"E8": "s9"}},
            "s9": {"on": {"E9": "s10"}},
            "s10": {"type": "final"},
        },
    },
    "starTopology": {
        "id": "starTopology",
        "initial": "hub",
        "states": {
            "hub": {
                "on": {
                    "GO_1": "spoke1",
                    "GO_2": "spoke2",
                    "GO_3": "spoke3",
                    "GO_4": "spoke4",
                    "GO_5": "spoke5",
                    "GO_6": "spoke6",
                    "GO_7": "spoke7",
                    "GO_8": "spoke8",
                },
            },
            "spoke1": {"on": {"BACK": "hub"}},
            "spoke2": {"on": {"BACK": "hub"}},
            "spoke3": {"on": {"BACK": "hub"}},
            "spoke4": {"on": {"BACK": "hub"}},
            "spoke5": {"on": {"BACK": "hub"}},
            "spoke6": {"on": {"BACK": "hub"}},
            "spoke7": {"on": {"BACK": "hub"}},
            "spoke8": {"on": {"BACK": "hub"}},
        },
    },
    "manyEvents": {
        "id": "manyEvents",
        "initial": "idle",
        "states": {
            "idle": {
                "on": {
                    "CREATE": "creating",
                    "EDIT": "editing",
                    "DELETE": "deleting",
                    "ARCHIVE": "archiving",
                    "EXPORT": "exporting",
                },
            },
            "creating": {
                "on": {
                    "SAVE": "idle",
                    "CANCEL": "idle",
                    "VALIDATE": "creating",
                    "PREVIEW": "creating",
                },
            },
            "editing": {
                "on": {
                    "SAVE": "idle",
                    "CANCEL": "idle",
                    "UNDO": "editing",
                    "REDO": "editing",
                },
            },
            "deleting": {
                "on": {
                    "CONFIRM_DELETE": "idle",
                    "CANCEL": "idle",
                    "SOFT_DELETE": "idle",
                    "HARD_DELETE": "idle",
                },
            },
            "archiving": {
                "on": {
                    "CONFIRM_ARCHIVE": "idle",
                    "CANCEL": "idle",
                    "SCHEDULE_ARCHIVE": "archiving",
                },
            },
            "exporting": {
                "on": {
                    "EXPORT_CSV": "idle",
                    "EXPORT_JSON": "idle",
                    "EXPORT_PDF": "idle",
                    "CANCEL": "idle",
                },
            },
        },
    },
    "fullFeatureLarge": {
        "id": "fullFeatureLarge",
        "initial": "init",
        "context": {
            "userId": None,
            "retries": 0,
            "data": None,
            "error": None,
        },
        "states": {
            "init": {
                "entry": "initialize",
                "on": {"START": {"target": "auth", "actions": "logStart"}},
            },
            "auth": {
                "initial": "login",
                "states": {
                    "login": {
                        "on": {
                            "SUBMIT": {
                                "target": "verifying",
                                "guard": "credentialsPresent",
                                "actions": "captureCredentials",
                            },
                        },
                    },
                    "verifying": {
                        "invoke": {
                            "src": "authService",
                            "onDone": {
                                "target": "#fullFeatureLarge.dashboard",
                                "actions": "setUserId",
                            },
                            "onError": {
                                "target": "login",
                                "actions": "setError",
                            },
                        },
                    },
                },
            },
            "dashboard": {
                "entry": "loadDashboard",
                "on": {
                    "FETCH_DATA": "fetching",
                    "SETTINGS": "settings",
                    "LOGOUT": {
                        "target": "auth",
                        "actions": "clearSession",
                    },
                },
            },
            "fetching": {
                "invoke": {
                    "src": "fetchDashboardData",
                    "onDone": {
                        "target": "dashboard",
                        "actions": "setData",
                    },
                    "onError": {
                        "target": "retrying",
                        "actions": "setError",
                    },
                },
            },
            "retrying": {
                "entry": "incrementRetries",
                "after": {
                    "2000": [
                        {
                            "target": "fetching",
                            "guard": "canRetry",
                        },
                        {"target": "failed"},
                    ],
                },
            },
            "failed": {
                "entry": "notifyFailure",
                "on": {
                    "RETRY": {
                        "target": "fetching",
                        "actions": "resetRetries",
                    },
                    "LOGOUT": {
                        "target": "auth",
                        "actions": "clearSession",
                    },
                },
            },
            "settings": {
                "on": {
                    "SAVE_SETTINGS": {
                        "target": "dashboard",
                        "actions": "applySettings",
                    },
                    "CANCEL": "dashboard",
                },
            },
        },
    },
    "wideParallel": {
        "id": "wideParallel",
        "initial": "active",
        "states": {
            "active": {
                "type": "parallel",
                "states": {
                    "region1": {
                        "initial": "r1a",
                        "states": {
                            "r1a": {"on": {"R1_NEXT": "r1b"}},
                            "r1b": {"on": {"R1_NEXT": "r1c"}},
                            "r1c": {"on": {"R1_RESET": "r1a"}},
                        },
                    },
                    "region2": {
                        "initial": "r2a",
                        "states": {
                            "r2a": {"on": {"R2_NEXT": "r2b"}},
                            "r2b": {"on": {"R2_NEXT": "r2c"}},
                            "r2c": {"on": {"R2_RESET": "r2a"}},
                        },
                    },
                    "region3": {
                        "initial": "r3a",
                        "states": {
                            "r3a": {"on": {"R3_NEXT": "r3b"}},
                            "r3b": {"on": {"R3_NEXT": "r3c"}},
                            "r3c": {"on": {"R3_RESET": "r3a"}},
                        },
                    },
                    "region4": {
                        "initial": "r4a",
                        "states": {
                            "r4a": {"on": {"R4_NEXT": "r4b"}},
                            "r4b": {"on": {"R4_NEXT": "r4c"}},
                            "r4c": {"on": {"R4_RESET": "r4a"}},
                        },
                    },
                    "region5": {
                        "initial": "r5a",
                        "states": {
                            "r5a": {"on": {"R5_NEXT": "r5b"}},
                            "r5b": {"on": {"R5_NEXT": "r5c"}},
                            "r5c": {"on": {"R5_RESET": "r5a"}},
                        },
                    },
                },
            },
        },
    },
    # ===================================================================
    # I. Real-World Domain Machines  (4)
    # ===================================================================
    "ecommerceCheckout": {
        "id": "ecommerceCheckout",
        "initial": "browsing",
        "context": {
            "cart": [],
            "total": 0,
            "paymentMethod": None,
            "orderId": None,
        },
        "states": {
            "browsing": {
                "on": {
                    "ADD_TO_CART": {
                        "target": "browsing",
                        "actions": "addToCart",
                    },
                    "VIEW_CART": {
                        "target": "cartView",
                        "guard": "cartNotEmpty",
                    },
                },
            },
            "cartView": {
                "entry": "calculateTotal",
                "on": {
                    "REMOVE_ITEM": {
                        "target": "cartView",
                        "actions": "removeItem",
                    },
                    "CHECKOUT": {
                        "target": "checkout",
                        "guard": "cartNotEmpty",
                    },
                    "CONTINUE_SHOPPING": "browsing",
                },
            },
            "checkout": {
                "initial": "shippingInfo",
                "states": {
                    "shippingInfo": {
                        "on": {
                            "SUBMIT_SHIPPING": {
                                "target": "paymentInfo",
                                "guard": "shippingValid",
                                "actions": "saveShipping",
                            },
                        },
                    },
                    "paymentInfo": {
                        "on": {
                            "SUBMIT_PAYMENT": {
                                "target": "reviewing",
                                "guard": "paymentValid",
                                "actions": "savePayment",
                            },
                            "BACK": "shippingInfo",
                        },
                    },
                    "reviewing": {
                        "on": {
                            "CONFIRM": {
                                "target": "#ecommerceCheckout.processing",
                            },
                            "BACK": "paymentInfo",
                        },
                    },
                },
                "on": {"CANCEL_CHECKOUT": "cartView"},
            },
            "processing": {
                "invoke": {
                    "src": "processPayment",
                    "onDone": {
                        "target": "confirmation",
                        "actions": "setOrderId",
                    },
                    "onError": {
                        "target": "paymentFailed",
                        "actions": "setPaymentError",
                    },
                },
            },
            "paymentFailed": {
                "on": {
                    "RETRY_PAYMENT": "processing",
                    "CANCEL": "cartView",
                },
            },
            "confirmation": {
                "entry": ["sendConfirmationEmail", "clearCart"],
                "type": "final",
            },
        },
    },
    "videoPlayer": {
        "id": "videoPlayer",
        "initial": "idle",
        "context": {
            "currentTime": 0,
            "duration": 0,
            "volume": 100,
            "src": None,
        },
        "states": {
            "idle": {
                "on": {
                    "LOAD": {
                        "target": "loading",
                        "actions": "setSrc",
                    },
                },
            },
            "loading": {
                "invoke": {
                    "src": "loadMedia",
                    "onDone": {
                        "target": "ready",
                        "actions": "setDuration",
                    },
                    "onError": "error",
                },
            },
            "ready": {
                "entry": "showControls",
                "on": {"PLAY": "playing"},
            },
            "playing": {
                "entry": "startPlayback",
                "exit": "pausePlayback",
                "on": {
                    "PAUSE": "paused",
                    "BUFFER": "buffering",
                    "END": "ended",
                    "SEEK": {
                        "target": "playing",
                        "actions": "updateCurrentTime",
                    },
                    "SET_VOLUME": {
                        "target": "playing",
                        "actions": "updateVolume",
                    },
                },
            },
            "paused": {
                "on": {
                    "PLAY": "playing",
                    "SEEK": {
                        "target": "paused",
                        "actions": "updateCurrentTime",
                    },
                },
            },
            "buffering": {
                "after": {
                    "10000": {
                        "target": "error",
                        "actions": "logBufferTimeout",
                    },
                },
                "on": {
                    "BUFFER_COMPLETE": "playing",
                    "PAUSE": "paused",
                },
            },
            "error": {
                "entry": "logError",
                "on": {
                    "RETRY": "loading",
                    "RESET": "idle",
                },
            },
            "ended": {
                "entry": "showReplay",
                "on": {
                    "REPLAY": {
                        "target": "playing",
                        "actions": "resetCurrentTime",
                    },
                    "LOAD": {
                        "target": "loading",
                        "actions": "setSrc",
                    },
                },
            },
        },
    },
    "formWizard": {
        "id": "formWizard",
        "initial": "step1",
        "context": {
            "personalInfo": None,
            "address": None,
            "preferences": None,
            "errors": [],
        },
        "states": {
            "step1": {
                "initial": "editing",
                "states": {
                    "editing": {
                        "on": {
                            "NEXT": {
                                "target": "validating",
                                "actions": "savePersonalInfo",
                            },
                        },
                    },
                    "validating": {
                        "invoke": {
                            "src": "validatePersonalInfo",
                            "onDone": "#formWizard.step2",
                            "onError": {
                                "target": "editing",
                                "actions": "setErrors",
                            },
                        },
                    },
                },
            },
            "step2": {
                "initial": "editing",
                "states": {
                    "editing": {
                        "on": {
                            "NEXT": {
                                "target": "validating",
                                "actions": "saveAddress",
                            },
                            "BACK": "#formWizard.step1",
                        },
                    },
                    "validating": {
                        "invoke": {
                            "src": "validateAddress",
                            "onDone": "#formWizard.step3",
                            "onError": {
                                "target": "editing",
                                "actions": "setErrors",
                            },
                        },
                    },
                },
            },
            "step3": {
                "on": {
                    "SUBMIT": {
                        "target": "submitting",
                        "guard": "allFieldsComplete",
                        "actions": "savePreferences",
                    },
                    "BACK": "step2",
                },
            },
            "submitting": {
                "invoke": {
                    "src": "submitForm",
                    "onDone": {
                        "target": "complete",
                        "actions": "showSuccess",
                    },
                    "onError": {
                        "target": "step3",
                        "actions": "setErrors",
                    },
                },
            },
            "complete": {"type": "final"},
        },
    },
    "cicdPipeline": {
        "id": "cicdPipeline",
        "initial": "source",
        "context": {
            "commitSha": None,
            "buildId": None,
            "testResults": None,
            "deploymentUrl": None,
            "rollbackTarget": None,
        },
        "states": {
            "source": {
                "on": {
                    "PUSH": {
                        "target": "building",
                        "actions": "setCommitSha",
                    },
                },
            },
            "building": {
                "entry": "logBuildStart",
                "invoke": {
                    "src": "buildProject",
                    "onDone": {
                        "target": "testing",
                        "actions": "setBuildId",
                    },
                    "onError": {
                        "target": "buildFailed",
                        "actions": "logBuildError",
                    },
                },
            },
            "buildFailed": {
                "entry": "notifyBuildFailure",
                "on": {
                    "RETRY": "building",
                    "ABORT": "aborted",
                },
            },
            "testing": {
                "invoke": {
                    "src": "runTests",
                    "onDone": [
                        {
                            "target": "deploying",
                            "guard": "allTestsPassed",
                            "actions": "setTestResults",
                        },
                        {
                            "target": "testsFailed",
                            "actions": "setTestResults",
                        },
                    ],
                    "onError": {
                        "target": "testsFailed",
                        "actions": "logTestError",
                    },
                },
            },
            "testsFailed": {
                "entry": "notifyTestFailure",
                "on": {
                    "RETRY": "testing",
                    "ABORT": "aborted",
                },
            },
            "deploying": {
                "entry": "logDeployStart",
                "invoke": {
                    "src": "deployToStaging",
                    "onDone": {
                        "target": "verifying",
                        "actions": "setDeploymentUrl",
                    },
                    "onError": {
                        "target": "deployFailed",
                        "actions": "logDeployError",
                    },
                },
            },
            "deployFailed": {
                "entry": "notifyDeployFailure",
                "on": {
                    "RETRY": "deploying",
                    "ROLLBACK": {
                        "target": "rollingBack",
                        "actions": "setRollbackTarget",
                    },
                    "ABORT": "aborted",
                },
            },
            "verifying": {
                "after": {
                    "30000": {
                        "target": "production",
                        "guard": "healthCheckPassed",
                    },
                },
                "on": {
                    "APPROVE": "production",
                    "ROLLBACK": {
                        "target": "rollingBack",
                        "actions": "setRollbackTarget",
                    },
                },
            },
            "production": {
                "entry": ["notifyDeploySuccess", "updateDashboard"],
                "type": "final",
            },
            "rollingBack": {
                "invoke": {
                    "src": "performRollback",
                    "onDone": {
                        "target": "source",
                        "actions": "logRollbackComplete",
                    },
                    "onError": {
                        "target": "aborted",
                        "actions": "logRollbackError",
                    },
                },
            },
            "aborted": {
                "entry": "notifyAborted",
                "type": "final",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


def _generate_and_validate(
    machine_id: str,
    config: Dict[str, Any],
    template: str,
    tmp_dir: Path,
    *,
    log: bool = True,
    file_count: int = 2,
) -> Tuple[bool, str]:
    """Generate code for *config* x *template*, then compile + import it.

    Returns ``(True, "OK")`` on success, ``(False, error_message)`` on failure.
    """
    # 1. Extract logic names from config
    actions, guards, services = extract_logic_names(config)
    machine_name = camel_to_snake(config.get("id", machine_id))

    # 2. Async mode: JSON templates default async, pythonic default sync
    is_async = not template.startswith("pythonic")

    # 3. Build GenerationContext
    ctx = GenerationContext(
        actions=actions,
        guards=guards,
        services=services,
        is_async=is_async,
        log=log,
        machine_name=machine_name,
        machine_id=config.get("id", machine_id),
        machine_names=[machine_name],
        machine_ids=[config.get("id", machine_id)],
        file_count=file_count,
        configs=[config],
        json_filenames=[f"{machine_name}.json"],
        hierarchy=False,
        sleep=True,
        sleep_time=1,
        loader=True,
        style=None,
    )

    strategy = get_strategy(template)
    safe_tpl = template.replace("-", "_")
    mode = f"fc{file_count}_log{'Y' if log else 'N'}"
    sub_dir = tmp_dir / f"{machine_name}__{safe_tpl}__{mode}"
    sub_dir.mkdir(parents=True, exist_ok=True)

    errors: List[str] = []

    # 4. Generate logic + runner
    try:
        logic_code = strategy.generate_logic(ctx)
    except Exception as exc:
        return False, f"generate_logic() raised: {exc}"
    try:
        runner_code = strategy.generate_runner(ctx)
    except Exception as exc:
        return False, f"generate_runner() raised: {exc}"

    logic_path = sub_dir / f"{machine_name}_logic.py"
    runner_path = sub_dir / f"{machine_name}_runner.py"
    logic_path.write_text(logic_code, encoding="utf-8")
    runner_path.write_text(runner_code, encoding="utf-8")

    # 5. py_compile both files
    for fpath in [logic_path, runner_path]:
        try:
            py_compile.compile(str(fpath), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"py_compile({fpath.name}): {exc}")

    # 6. importlib import logic file
    try:
        spec = importlib.util.spec_from_file_location(
            f"{machine_name}_logic__{safe_tpl}__{mode}",
            str(logic_path),
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as exc:
        errors.append(f"import({logic_path.name}): {exc}")

    if errors:
        return False, "; ".join(errors)
    return True, "OK"


# ---------------------------------------------------------------------------
# Test class 1: log=True, file_count=2 (default / most common)
# ---------------------------------------------------------------------------


class StressMachineTests(unittest.TestCase):
    """50 machines x 5 templates = 250 tests (log=True, file_count=2)."""

    _tmp_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="xsm_stress_"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)


def _make_test(
    machine_id: str,
    config: Dict[str, Any],
    template: str,
    *,
    log: bool = True,
    file_count: int = 2,
) -> Any:
    """Factory: create a test method for one (machine, template) pair."""

    def test_fn(self: unittest.TestCase) -> None:
        ok, msg = _generate_and_validate(
            machine_id,
            config,
            template,
            self._tmp_dir,  # type: ignore[attr-defined]
            log=log,
            file_count=file_count,
        )
        self.assertTrue(ok, f"[{machine_id} x {template}] {msg}")

    safe = template.replace("-", "_")
    test_fn.__name__ = f"test_{machine_id}__{safe}"
    test_fn.__doc__ = f"{machine_id} x {template}"
    return test_fn


# --- register 250 tests: log=True, file_count=2 ---
for _mid, _cfg in MACHINES.items():
    for _tpl in TEMPLATES:
        _fn = _make_test(_mid, _cfg, _tpl, log=True, file_count=2)
        setattr(StressMachineTests, _fn.__name__, _fn)


# ---------------------------------------------------------------------------
# Test class 2: log=False, file_count=2 (historically bug-prone)
# ---------------------------------------------------------------------------


class StressMachineTestsLogFalse(unittest.TestCase):
    """50 machines x 5 templates = 250 tests (log=False, file_count=2)."""

    _tmp_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="xsm_stress_nolog_"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)


for _mid, _cfg in MACHINES.items():
    for _tpl in TEMPLATES:
        _fn = _make_test(_mid, _cfg, _tpl, log=False, file_count=2)
        setattr(StressMachineTestsLogFalse, _fn.__name__, _fn)


# ---------------------------------------------------------------------------
# Test class 3: log=True, file_count=1 (merged files — most complex path)
# ---------------------------------------------------------------------------


class StressMachineTestsSingleFile(unittest.TestCase):
    """50 machines x 5 templates = 250 tests (log=True, file_count=1)."""

    _tmp_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="xsm_stress_fc1_"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)


for _mid, _cfg in MACHINES.items():
    for _tpl in TEMPLATES:
        _fn = _make_test(_mid, _cfg, _tpl, log=True, file_count=1)
        setattr(StressMachineTestsSingleFile, _fn.__name__, _fn)
