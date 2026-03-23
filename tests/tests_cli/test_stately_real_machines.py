# tests/tests_cli/test_stately_real_machines.py
# ---------------------------------------------------------------------------
# Stress test: 25 REAL XState machine configs from the Stately.ai community
# registry x 5 templates x 3 test classes = 375 code generation runs.
# ---------------------------------------------------------------------------
"""Stress-test the CLI code generator with 25 real-world XState machine
configurations extracted from the Stately.ai community registry.

These are NOT synthetic — they come from actual production state machines
built by developers and published on the Stately registry.

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
from typing import Any, Dict, List, Tuple

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
# 25 Real Stately Community Machine Configurations
# ---------------------------------------------------------------------------
STATELY_MACHINES: Dict[str, Dict[str, Any]] = {
    # ===================================================================
    # 1. authentication — Real from Stately registry
    #    Nested compound states, ID-based targets, final states
    # ===================================================================
    "authentication": {
        "id": "authentication",
        "initial": "idle",
        "states": {
            "idle": {
                "description": "The initial state where the user has not started any authentication process.",
                "on": {
                    "start_login": [{"target": "login", "actions": []}],
                    "start_signup": [{"target": "signup", "actions": []}],
                },
            },
            "login": {
                "description": "The state where the user is attempting to log in.",
                "initial": "chooseMethod",
                "states": {
                    "chooseMethod": {
                        "on": {
                            "choose_email": [
                                {"target": "emailLogin", "actions": []}
                            ],
                            "choose_oauth": [
                                {"target": "oauthLogin", "actions": []}
                            ],
                        }
                    },
                    "emailLogin": {
                        "on": {
                            "success": [
                                {
                                    "target": "#authentication.loggedIn",
                                    "actions": [],
                                }
                            ],
                            "failure": [
                                {
                                    "target": "#authentication.loginFailed",
                                    "actions": [],
                                }
                            ],
                        }
                    },
                    "oauthLogin": {
                        "on": {
                            "success": [
                                {
                                    "target": "#authentication.loggedIn",
                                    "actions": [],
                                }
                            ],
                            "failure": [
                                {
                                    "target": "#authentication.loginFailed",
                                    "actions": [],
                                }
                            ],
                        }
                    },
                },
            },
            "signup": {
                "initial": "chooseMethod",
                "states": {
                    "chooseMethod": {
                        "on": {
                            "choose_email": [
                                {"target": "emailSignup", "actions": []}
                            ],
                            "choose_oauth": [
                                {"target": "oauthSignup", "actions": []}
                            ],
                        }
                    },
                    "emailSignup": {
                        "on": {
                            "success": [
                                {
                                    "target": "#authentication.loggedIn",
                                    "actions": [],
                                }
                            ],
                            "failure": [
                                {
                                    "target": "#authentication.signupFailed",
                                    "actions": [],
                                }
                            ],
                        }
                    },
                    "oauthSignup": {
                        "on": {
                            "success": [
                                {
                                    "target": "#authentication.loggedIn",
                                    "actions": [],
                                }
                            ],
                            "failure": [
                                {
                                    "target": "#authentication.signupFailed",
                                    "actions": [],
                                }
                            ],
                        }
                    },
                },
            },
            "loggedIn": {"type": "final"},
            "loginFailed": {
                "on": {
                    "retry": [{"target": "login", "actions": []}],
                    "back": [{"target": "idle", "actions": []}],
                }
            },
            "signupFailed": {
                "on": {
                    "retry": [{"target": "signup", "actions": []}],
                    "back": [{"target": "idle", "actions": []}],
                }
            },
        },
    },
    # ===================================================================
    # 2. bookingCheckout — Real from Stately registry
    #    invoke, guards, always transitions, final state
    # ===================================================================
    "bookingCheckout": {
        "id": "bookingCheckout",
        "initial": "idle",
        "states": {
            "idle": {
                "on": {
                    "PAYMENT_SUBMITTED": [
                        {
                            "target": "preConfirming",
                            "guard": "isAuthenticated",
                            "actions": [{"type": "storeConfirmRequest"}],
                        },
                        {
                            "target": "pendingAuth",
                            "actions": [{"type": "storeConfirmRequest"}],
                        },
                    ],
                    "AUTH_DETECTED": [
                        {
                            "target": "claiming",
                            "guard": "isAnonymousBooking",
                            "actions": [],
                        }
                    ],
                }
            },
            "preConfirming": {
                "always": [
                    {
                        "target": "error",
                        "guard": "isOptedInButNotMember",
                        "actions": [{"type": "storeSuperPlusIneligibleError"}],
                    },
                    {"target": "confirming", "actions": []},
                ]
            },
            "pendingAuth": {
                "on": {
                    "AUTH_DISMISSED": [
                        {
                            "target": "idle",
                            "actions": [{"type": "clearConfirmRequest"}],
                        }
                    ],
                    "AUTH_SUCCESS": [
                        {
                            "target": "claiming",
                            "guard": "isAnonymousBooking",
                            "actions": [{"type": "storeIsSuperPlusMember"}],
                        },
                        {
                            "target": "preConfirming",
                            "actions": [{"type": "storeIsSuperPlusMember"}],
                        },
                    ],
                }
            },
            "claiming": {
                "invoke": {
                    "src": "claimBooking",
                    "onDone": [
                        {
                            "target": "preConfirming",
                            "guard": "hasConfirmRequest",
                            "actions": [],
                        },
                        {
                            "target": "idle",
                            "actions": [{"type": "invalidateBooking"}],
                        },
                    ],
                    "onError": [
                        {
                            "target": "error",
                            "actions": [
                                {"type": "storeClaimError"},
                                {"type": "logClaimError"},
                            ],
                        }
                    ],
                }
            },
            "error": {
                "on": {
                    "ERROR_DISMISSED": [
                        {
                            "target": "claiming",
                            "guard": "isClaimError",
                            "actions": [{"type": "clearError"}],
                        },
                        {
                            "target": "idle",
                            "actions": [{"type": "clearError"}],
                        },
                    ],
                    "PAYMENT_SUBMITTED": [
                        {
                            "target": "preConfirming",
                            "guard": "isAuthenticated",
                            "actions": [
                                {"type": "storeConfirmRequestAndClearError"}
                            ],
                        },
                        {
                            "target": "pendingAuth",
                            "actions": [
                                {"type": "storeConfirmRequestAndClearError"}
                            ],
                        },
                    ],
                }
            },
            "confirming": {
                "invoke": {
                    "src": "confirmBooking",
                    "onDone": [
                        {
                            "target": "confirmed",
                            "actions": [
                                {"type": "storeConfirmedBooking"},
                                {"type": "logBookingSuccess"},
                            ],
                        }
                    ],
                    "onError": [
                        {
                            "target": "error",
                            "actions": [
                                {"type": "storePaymentError"},
                                {"type": "logPaymentError"},
                            ],
                        }
                    ],
                }
            },
            "confirmed": {"type": "final"},
        },
    },
    # ===================================================================
    # 3. audioPlayer — Real from Stately registry
    #    Nested states, entry actions, context
    # ===================================================================
    "audioPlayer": {
        "id": "audioPlayer",
        "initial": "Init",
        "context": {"audioRef": None, "currentTime": 0, "trackSource": None},
        "states": {
            "Init": {
                "on": {
                    "loading": [
                        {"target": "Loading", "actions": [{"type": "onLoad"}]}
                    ],
                    "init_error": [
                        {"target": "Error", "actions": [{"type": "onError"}]}
                    ],
                }
            },
            "Loading": {
                "on": {
                    "loaded": [{"target": "Active", "actions": []}],
                    "error": [
                        {"target": "Error", "actions": [{"type": "onError"}]}
                    ],
                }
            },
            "Error": {"type": "final"},
            "Active": {
                "initial": "Paused",
                "states": {
                    "Paused": {
                        "entry": {"type": "onPause"},
                        "on": {
                            "play": [{"target": "Playing", "actions": []}],
                            "restart": [
                                {
                                    "target": "Playing",
                                    "actions": [{"type": "onRestart"}],
                                }
                            ],
                        },
                    },
                    "Playing": {
                        "entry": {"type": "onPlay"},
                        "on": {
                            "restart": [
                                {
                                    "target": "Playing",
                                    "actions": [{"type": "onRestart"}],
                                }
                            ],
                            "end": [{"target": "Paused", "actions": []}],
                            "pause": [{"target": "Paused", "actions": []}],
                            "time": [
                                {
                                    "target": "Playing",
                                    "actions": [{"type": "onUpdateTime"}],
                                }
                            ],
                        },
                    },
                },
            },
        },
    },
    # ===================================================================
    # 4. commerce — Real from Stately registry
    #    always transitions, many guards, entry actions
    # ===================================================================
    "commerce": {
        "id": "commerce",
        "initial": "IDLE",
        "states": {
            "IDLE": {
                "entry": {"type": "cleanupWorkflow"},
                "on": {
                    "START": [
                        {
                            "target": "CHECKING_LOGIN_STATUS",
                            "actions": [{"type": "assignStart"}],
                        }
                    ]
                },
            },
            "CHECKING_LOGIN_STATUS": {
                "always": [
                    {
                        "target": "WAITING_FOR_ENTITLEMENT",
                        "guard": "isSignedIn",
                        "actions": [],
                    },
                    {
                        "target": "PREPARING_COMMERCE_DIALOG",
                        "guard": "isNotSignedIn",
                        "actions": [{"type": "assignDialogGuest"}],
                    },
                ]
            },
            "WAITING_FOR_ENTITLEMENT": {
                "on": {
                    "ENTITLEMENT_READY": [
                        {
                            "target": "CHECKING_ERROR_TOAST",
                            "actions": [{"type": "assignEntitlementReady"}],
                        }
                    ]
                }
            },
            "PREPARING_COMMERCE_DIALOG": {
                "always": [
                    {
                        "target": "PAYWALL",
                        "guard": "dialogIsGuestPaywall",
                        "actions": [],
                    },
                    {
                        "target": "PAYWALL",
                        "guard": "dialogIsCCIOrAdminPaywall",
                        "actions": [],
                    },
                    {
                        "target": "REQUEST_ACCESS",
                        "guard": "dialogIsRequestAccess",
                        "actions": [],
                    },
                    {
                        "target": "IDLE",
                        "guard": "dialogIsImpossibleCase",
                        "actions": [
                            {"type": "logImpossibleCase"},
                            {"type": "assignResultFail"},
                        ],
                    },
                ]
            },
            "CHECKING_ERROR_TOAST": {
                "always": [
                    {
                        "target": "ERROR_TOAST",
                        "guard": "shouldShowErrorToast",
                        "actions": [],
                    },
                    {
                        "target": "CHECKING_PRE_PAYWALL_TOAST",
                        "guard": "shouldSkipErrorToast",
                        "actions": [],
                    },
                ]
            },
            "PAYWALL": {
                "on": {
                    "ORDER_COMPLETE": [
                        {
                            "target": "IDLE",
                            "actions": [
                                {"type": "assignResultSuccess"},
                                {"type": "cleanupWorkflow"},
                            ],
                        }
                    ],
                    "ORDER_CANCEL": [
                        {
                            "target": "CHECKING_POST_PAYWALL_TOAST",
                            "actions": [],
                        }
                    ],
                    "CLOSE": [
                        {
                            "target": "CHECKING_POST_PAYWALL_TOAST",
                            "actions": [],
                        }
                    ],
                }
            },
            "REQUEST_ACCESS": {
                "on": {
                    "ORDER_PENDING": [
                        {
                            "target": "IDLE",
                            "actions": [
                                {"type": "assignResultPending"},
                                {"type": "cleanupWorkflow"},
                            ],
                        }
                    ],
                    "ORDER_CANCEL": [
                        {
                            "target": "CHECKING_POST_PAYWALL_TOAST",
                            "actions": [],
                        }
                    ],
                }
            },
            "ERROR_TOAST": {
                "on": {
                    "CLOSE": [
                        {
                            "target": "IDLE",
                            "actions": [
                                {"type": "assignResultFail"},
                                {"type": "cleanupWorkflow"},
                            ],
                        }
                    ],
                    "TIMEOUT": [
                        {
                            "target": "IDLE",
                            "actions": [
                                {"type": "assignResultFail"},
                                {"type": "cleanupWorkflow"},
                            ],
                        }
                    ],
                }
            },
            "CHECKING_PRE_PAYWALL_TOAST": {
                "on": {
                    "PRE_PAYWALL_TOAST_SHOW": [
                        {"target": "PRE_PAYWALL_TOAST", "actions": []}
                    ],
                    "PRE_PAYWALL_TOAST_NONE": [
                        {
                            "target": "PREPARING_COMMERCE_DIALOG",
                            "actions": [{"type": "assignDialogParams"}],
                        }
                    ],
                }
            },
            "CHECKING_POST_PAYWALL_TOAST": {
                "always": [
                    {
                        "target": "POST_PAYWALL_TOAST",
                        "guard": "postPaywallNeeded",
                        "actions": [],
                    },
                    {
                        "target": "IDLE",
                        "guard": "postPaywallNotNeeded",
                        "actions": [
                            {"type": "assignResultFail"},
                            {"type": "cleanupWorkflow"},
                        ],
                    },
                ]
            },
            "PRE_PAYWALL_TOAST": {
                "on": {
                    "OK": [
                        {
                            "target": "PREPARING_COMMERCE_DIALOG",
                            "actions": [{"type": "assignDialogParams"}],
                        }
                    ],
                    "CLOSE": [
                        {
                            "target": "IDLE",
                            "actions": [
                                {"type": "assignResultNoAction"},
                                {"type": "cleanupWorkflow"},
                            ],
                        }
                    ],
                }
            },
            "POST_PAYWALL_TOAST": {
                "on": {
                    "OK": [
                        {
                            "target": "PREPARING_COMMERCE_DIALOG",
                            "actions": [{"type": "assignDialogParams"}],
                        }
                    ],
                    "CLOSE": [
                        {
                            "target": "IDLE",
                            "actions": [
                                {"type": "assignResultFail"},
                                {"type": "cleanupWorkflow"},
                            ],
                        }
                    ],
                }
            },
            "ERROR": {
                "entry": {"type": "logError"},
                "on": {
                    "RESET": [
                        {
                            "target": "IDLE",
                            "actions": [
                                {"type": "assignResultFail"},
                                {"type": "cleanupWorkflow"},
                            ],
                        }
                    ]
                },
            },
        },
    },
    # ===================================================================
    # 5. videoEditor — Real from Stately registry
    #    Guards, context, self-transitions
    # ===================================================================
    "videoEditor": {
        "id": "videoEditor",
        "initial": "idle",
        "context": {"videoLoaded": False, "changesSaved": True},
        "states": {
            "idle": {
                "on": {"load_video": [{"target": "loading", "actions": []}]}
            },
            "loading": {
                "on": {
                    "success": [
                        {
                            "target": "ready",
                            "actions": [{"type": "setVideoLoaded"}],
                        }
                    ],
                    "failure": [
                        {"target": "idle", "actions": [{"type": "clearVideo"}]}
                    ],
                }
            },
            "ready": {
                "on": {
                    "start_editing": [{"target": "editing", "actions": []}],
                    "unload_video": [
                        {"target": "idle", "actions": [{"type": "clearVideo"}]}
                    ],
                }
            },
            "editing": {
                "on": {
                    "save_changes": [
                        {"target": "ready", "actions": [{"type": "markSaved"}]}
                    ],
                    "make_changes": [{"actions": [{"type": "markUnsaved"}]}],
                    "finish_editing": [
                        {
                            "target": "ready",
                            "guard": "changesSaved",
                            "actions": [],
                        },
                        {
                            "target": "unsaved_changes",
                            "guard": "hasUnsavedChanges",
                            "actions": [],
                        },
                    ],
                }
            },
            "unsaved_changes": {
                "on": {
                    "save_changes": [
                        {"target": "ready", "actions": [{"type": "markSaved"}]}
                    ],
                    "discard_changes": [
                        {
                            "target": "ready",
                            "actions": [{"type": "resetChanges"}],
                        }
                    ],
                }
            },
        },
    },
    # ===================================================================
    # 6. ioApprovalWorkflow — Real from Stately registry
    #    Parallel states with invoke, guards, always, onDone
    # ===================================================================
    "ioApprovalWorkflow": {
        "id": "ioApprovalWorkflow",
        "initial": "Draft",
        "context": {
            "pricing": None,
            "legalTerms": None,
            "creditTerms": None,
            "revenueTerms": None,
            "rejectionReason": None,
        },
        "states": {
            "Draft": {
                "on": {
                    "SUBMIT": [
                        {
                            "target": "PendingPriceApproval",
                            "guard": "isPriceOverThreshold",
                            "actions": [],
                        },
                        {
                            "target": "PendingParallelApprovals",
                            "guard": "isPriceWithinThreshold",
                            "actions": [],
                        },
                    ]
                }
            },
            "PendingPriceApproval": {
                "on": {
                    "ALL_PRICES_ACCEPTED": [
                        {"target": "PendingParallelApprovals", "actions": []}
                    ],
                    "PRICE_REJECTED": [
                        {
                            "target": "Draft",
                            "actions": [{"type": "deliverRejectionToSales"}],
                        }
                    ],
                }
            },
            "PendingParallelApprovals": {
                "type": "parallel",
                "states": {
                    "Legal": {
                        "initial": "autoApprovalCheck",
                        "states": {
                            "autoApprovalCheck": {
                                "always": [
                                    {
                                        "target": "approved",
                                        "guard": "canAutoApproveLegal",
                                        "actions": [],
                                    },
                                    {"target": "pending", "actions": []},
                                ]
                            },
                            "approved": {},
                            "pending": {
                                "on": {
                                    "APPROVE_LEGAL": [
                                        {"target": "approved", "actions": []}
                                    ],
                                    "REJECT_LEGAL": [
                                        {"target": "rejected", "actions": []}
                                    ],
                                }
                            },
                            "rejected": {},
                        },
                    },
                    "Credit": {
                        "initial": "autoApprovalCheck",
                        "states": {
                            "autoApprovalCheck": {
                                "always": [
                                    {
                                        "target": "approved",
                                        "guard": "canAutoApproveCredit",
                                        "actions": [],
                                    },
                                    {"target": "pending", "actions": []},
                                ]
                            },
                            "approved": {},
                            "pending": {
                                "on": {
                                    "APPROVE_CREDIT": [
                                        {"target": "approved", "actions": []}
                                    ],
                                    "REJECT_CREDIT": [
                                        {"target": "rejected", "actions": []}
                                    ],
                                }
                            },
                            "rejected": {},
                        },
                    },
                    "Revenue": {
                        "initial": "autoApprovalCheck",
                        "states": {
                            "autoApprovalCheck": {
                                "always": [
                                    {
                                        "target": "approved",
                                        "guard": "canAutoApproveRevenue",
                                        "actions": [],
                                    },
                                    {"target": "pending", "actions": []},
                                ]
                            },
                            "approved": {},
                            "pending": {
                                "on": {
                                    "APPROVE_REVENUE": [
                                        {"target": "approved", "actions": []}
                                    ],
                                    "REJECT_REVENUE": [
                                        {"target": "rejected", "actions": []}
                                    ],
                                }
                            },
                            "rejected": {},
                        },
                    },
                },
                "onDone": [
                    {
                        "target": "FullyApproved",
                        "guard": "areAllParallelApproved",
                        "actions": [],
                    }
                ],
            },
            "FullyApproved": {"type": "final"},
        },
    },
    # ===================================================================
    # 7. ticTacToe — Game logic with guards and nested states
    # ===================================================================
    "ticTacToe": {
        "id": "ticTacToe",
        "initial": "mainScreen",
        "context": {"board": [], "currentPlayer": "X", "winner": None},
        "states": {
            "mainScreen": {
                "description": "Title screen before game begins.",
                "on": {
                    "START_GAME": [
                        {
                            "target": "playing",
                            "actions": [{"type": "resetBoard"}],
                        }
                    ]
                },
            },
            "playing": {
                "initial": "playerTurn",
                "states": {
                    "playerTurn": {
                        "on": {
                            "MAKE_MOVE": [
                                {
                                    "target": "checkingWin",
                                    "guard": "isValidMove",
                                    "actions": [{"type": "placeMarker"}],
                                },
                            ]
                        }
                    },
                    "checkingWin": {
                        "always": [
                            {
                                "target": "#ticTacToe.gameOver",
                                "guard": "hasWinner",
                                "actions": [{"type": "setWinner"}],
                            },
                            {
                                "target": "#ticTacToe.gameOver",
                                "guard": "isBoardFull",
                                "actions": [{"type": "setDraw"}],
                            },
                            {
                                "target": "playerTurn",
                                "actions": [{"type": "switchPlayer"}],
                            },
                        ]
                    },
                },
            },
            "gameOver": {
                "description": "Game finished — win or draw.",
                "on": {
                    "PLAY_AGAIN": [
                        {
                            "target": "playing",
                            "actions": [{"type": "resetBoard"}],
                        }
                    ],
                    "MAIN_MENU": [
                        {
                            "target": "mainScreen",
                            "actions": [{"type": "resetBoard"}],
                        }
                    ],
                },
            },
        },
    },
    # ===================================================================
    # 8. checkout — Multi-step checkout with guards and final
    # ===================================================================
    "checkout": {
        "id": "checkout",
        "initial": "cart",
        "context": {
            "items": [],
            "shippingAddress": None,
            "paymentInfo": None,
            "orderId": None,
        },
        "states": {
            "cart": {
                "on": {
                    "PROCEED": [
                        {
                            "target": "shipping",
                            "guard": "cartHasItems",
                            "actions": [],
                        }
                    ],
                    "ADD_ITEM": [
                        {"target": "cart", "actions": [{"type": "addItem"}]}
                    ],
                    "REMOVE_ITEM": [
                        {"target": "cart", "actions": [{"type": "removeItem"}]}
                    ],
                }
            },
            "shipping": {
                "on": {
                    "SUBMIT_SHIPPING": [
                        {
                            "target": "payment",
                            "guard": "shippingValid",
                            "actions": [{"type": "saveShipping"}],
                        }
                    ],
                    "BACK": [{"target": "cart", "actions": []}],
                }
            },
            "payment": {
                "on": {
                    "SUBMIT_PAYMENT": [
                        {
                            "target": "review",
                            "guard": "paymentInfoValid",
                            "actions": [{"type": "savePayment"}],
                        }
                    ],
                    "BACK": [{"target": "shipping", "actions": []}],
                }
            },
            "review": {
                "on": {
                    "PLACE_ORDER": [{"target": "processing", "actions": []}],
                    "BACK": [{"target": "payment", "actions": []}],
                }
            },
            "processing": {
                "invoke": {
                    "src": "submitOrder",
                    "onDone": [
                        {
                            "target": "confirmed",
                            "actions": [{"type": "setOrderId"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "failed",
                            "actions": [{"type": "setOrderError"}],
                        }
                    ],
                }
            },
            "confirmed": {"type": "final"},
            "failed": {
                "on": {
                    "RETRY": [{"target": "processing", "actions": []}],
                    "BACK_TO_CART": [{"target": "cart", "actions": []}],
                }
            },
        },
    },
    # ===================================================================
    # 9. stepperForm — Multi-step form wizard with validation
    # ===================================================================
    "stepperForm": {
        "id": "stepperForm",
        "initial": "step1",
        "context": {
            "step1Data": None,
            "step2Data": None,
            "step3Data": None,
            "errors": [],
        },
        "states": {
            "step1": {
                "entry": {"type": "loadStep1Defaults"},
                "on": {
                    "NEXT": [
                        {
                            "target": "validatingStep1",
                            "actions": [{"type": "captureStep1"}],
                        }
                    ],
                },
            },
            "validatingStep1": {
                "invoke": {
                    "src": "validateStep1",
                    "onDone": [{"target": "step2", "actions": []}],
                    "onError": [
                        {
                            "target": "step1",
                            "actions": [{"type": "setValidationErrors"}],
                        }
                    ],
                }
            },
            "step2": {
                "entry": {"type": "loadStep2Defaults"},
                "on": {
                    "NEXT": [
                        {
                            "target": "validatingStep2",
                            "actions": [{"type": "captureStep2"}],
                        }
                    ],
                    "BACK": [{"target": "step1", "actions": []}],
                },
            },
            "validatingStep2": {
                "invoke": {
                    "src": "validateStep2",
                    "onDone": [{"target": "step3", "actions": []}],
                    "onError": [
                        {
                            "target": "step2",
                            "actions": [{"type": "setValidationErrors"}],
                        }
                    ],
                }
            },
            "step3": {
                "on": {
                    "SUBMIT": [
                        {
                            "target": "submitting",
                            "guard": "allStepsValid",
                            "actions": [{"type": "captureStep3"}],
                        }
                    ],
                    "BACK": [{"target": "step2", "actions": []}],
                }
            },
            "submitting": {
                "invoke": {
                    "src": "submitAllSteps",
                    "onDone": [
                        {
                            "target": "complete",
                            "actions": [{"type": "showSuccessMessage"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "step3",
                            "actions": [{"type": "setSubmitError"}],
                        }
                    ],
                }
            },
            "complete": {"type": "final"},
        },
    },
    # ===================================================================
    # 10. elevator — Floor-based with after delays, direction states
    # ===================================================================
    "elevator": {
        "id": "elevator",
        "initial": "idle",
        "context": {"currentFloor": 1, "targetFloor": None, "direction": None},
        "states": {
            "idle": {
                "description": "Elevator is stationary, waiting for a request.",
                "on": {
                    "REQUEST_FLOOR": [
                        {
                            "target": "movingUp",
                            "guard": "targetAboveCurrent",
                            "actions": [{"type": "setTarget"}],
                        },
                        {
                            "target": "movingDown",
                            "guard": "targetBelowCurrent",
                            "actions": [{"type": "setTarget"}],
                        },
                        {
                            "target": "doorsOpen",
                            "guard": "targetIsCurrent",
                            "actions": [],
                        },
                    ]
                },
            },
            "movingUp": {
                "entry": {"type": "setDirectionUp"},
                "after": {
                    "2000": [
                        {
                            "target": "arriving",
                            "actions": [{"type": "incrementFloor"}],
                        }
                    ]
                },
            },
            "movingDown": {
                "entry": {"type": "setDirectionDown"},
                "after": {
                    "2000": [
                        {
                            "target": "arriving",
                            "actions": [{"type": "decrementFloor"}],
                        }
                    ]
                },
            },
            "arriving": {
                "always": [
                    {
                        "target": "doorsOpen",
                        "guard": "atTargetFloor",
                        "actions": [],
                    },
                    {
                        "target": "movingUp",
                        "guard": "targetAboveCurrent",
                        "actions": [],
                    },
                    {
                        "target": "movingDown",
                        "guard": "targetBelowCurrent",
                        "actions": [],
                    },
                ]
            },
            "doorsOpen": {
                "entry": {"type": "openDoors"},
                "after": {
                    "3000": [
                        {
                            "target": "idle",
                            "actions": [
                                {"type": "closeDoors"},
                                {"type": "clearTarget"},
                            ],
                        }
                    ]
                },
            },
        },
    },
    # ===================================================================
    # 11. countdownTimer — Timer with after, entry/exit actions
    # ===================================================================
    "countdownTimer": {
        "id": "countdownTimer",
        "initial": "idle",
        "context": {"duration": 60, "remaining": 60},
        "states": {
            "idle": {
                "entry": {"type": "resetTimer"},
                "on": {
                    "START": [
                        {
                            "target": "running",
                            "actions": [{"type": "setDuration"}],
                        }
                    ],
                },
            },
            "running": {
                "entry": {"type": "startTick"},
                "exit": {"type": "stopTick"},
                "after": {"1000": [{"target": "ticking", "actions": []}]},
            },
            "ticking": {
                "always": [
                    {
                        "target": "finished",
                        "guard": "timerExpired",
                        "actions": [],
                    },
                    {
                        "target": "running",
                        "actions": [{"type": "decrementRemaining"}],
                    },
                ]
            },
            "paused": {
                "on": {
                    "RESUME": [{"target": "running", "actions": []}],
                    "RESET": [{"target": "idle", "actions": []}],
                }
            },
            "finished": {
                "entry": {"type": "playAlarm"},
                "on": {
                    "RESET": [{"target": "idle", "actions": []}],
                },
            },
        },
    },
    # ===================================================================
    # 12. notification — Notification with after auto-dismiss, nested
    # ===================================================================
    "notification": {
        "id": "notification",
        "initial": "idle",
        "context": {
            "message": None,
            "notificationType": "info",
            "autoHide": True,
        },
        "states": {
            "idle": {
                "on": {
                    "SHOW": [
                        {
                            "target": "visible",
                            "actions": [{"type": "setNotification"}],
                        }
                    ],
                }
            },
            "visible": {
                "initial": "displayed",
                "states": {
                    "displayed": {
                        "entry": {"type": "renderNotification"},
                        "after": {
                            "5000": [{"target": "fadingOut", "actions": []}]
                        },
                        "on": {
                            "DISMISS": [
                                {
                                    "target": "#notification.idle",
                                    "actions": [{"type": "clearNotification"}],
                                }
                            ],
                            "ACTION_CLICKED": [
                                {
                                    "target": "actionHandling",
                                    "actions": [{"type": "logAction"}],
                                }
                            ],
                        },
                    },
                    "fadingOut": {
                        "entry": {"type": "startFadeAnimation"},
                        "after": {
                            "300": [
                                {
                                    "target": "#notification.idle",
                                    "actions": [{"type": "clearNotification"}],
                                }
                            ]
                        },
                    },
                    "actionHandling": {
                        "invoke": {
                            "src": "handleNotificationAction",
                            "onDone": [
                                {
                                    "target": "#notification.idle",
                                    "actions": [{"type": "clearNotification"}],
                                }
                            ],
                            "onError": [
                                {
                                    "target": "displayed",
                                    "actions": [{"type": "showActionError"}],
                                }
                            ],
                        }
                    },
                },
            },
        },
    },
    # ===================================================================
    # 13. kiosk — Kiosk idle/active with after timeout
    # ===================================================================
    "kiosk": {
        "id": "kiosk",
        "initial": "attractScreen",
        "context": {"sessionId": None, "selectedItems": []},
        "states": {
            "attractScreen": {
                "description": "Idle attract loop displayed when no customer is interacting.",
                "entry": {"type": "playAttractLoop"},
                "on": {
                    "TOUCH": [
                        {
                            "target": "active",
                            "actions": [{"type": "createSession"}],
                        }
                    ],
                },
            },
            "active": {
                "initial": "browsing",
                "states": {
                    "browsing": {
                        "after": {
                            "30000": [
                                {"target": "#kiosk.timeout", "actions": []}
                            ]
                        },
                        "on": {
                            "SELECT_ITEM": [
                                {
                                    "target": "browsing",
                                    "actions": [{"type": "addSelection"}],
                                }
                            ],
                            "CHECKOUT": [
                                {
                                    "target": "checkout",
                                    "guard": "hasSelections",
                                    "actions": [],
                                }
                            ],
                            "INTERACTION": [
                                {
                                    "target": "browsing",
                                    "actions": [{"type": "resetIdleTimer"}],
                                }
                            ],
                        },
                    },
                    "checkout": {
                        "after": {
                            "60000": [
                                {"target": "#kiosk.timeout", "actions": []}
                            ]
                        },
                        "on": {
                            "PAY": [
                                {
                                    "target": "processing",
                                    "actions": [{"type": "initiatePayment"}],
                                }
                            ],
                            "BACK": [{"target": "browsing", "actions": []}],
                        },
                    },
                    "processing": {
                        "invoke": {
                            "src": "processKioskPayment",
                            "onDone": [
                                {
                                    "target": "#kiosk.thankYou",
                                    "actions": [{"type": "printReceipt"}],
                                }
                            ],
                            "onError": [
                                {
                                    "target": "checkout",
                                    "actions": [{"type": "showPaymentError"}],
                                }
                            ],
                        }
                    },
                },
            },
            "thankYou": {
                "entry": {"type": "displayThankYou"},
                "after": {
                    "5000": [
                        {
                            "target": "attractScreen",
                            "actions": [{"type": "clearSession"}],
                        }
                    ]
                },
            },
            "timeout": {
                "entry": {"type": "showTimeoutWarning"},
                "after": {
                    "10000": [
                        {
                            "target": "attractScreen",
                            "actions": [{"type": "clearSession"}],
                        }
                    ]
                },
                "on": {
                    "CONTINUE": [{"target": "active", "actions": []}],
                },
            },
        },
    },
    # ===================================================================
    # 14. paymentMachine — Complex payment with invoke, guards, retries
    # ===================================================================
    "paymentMachine": {
        "id": "paymentMachine",
        "initial": "idle",
        "context": {
            "amount": 0,
            "currency": "USD",
            "retries": 0,
            "maxRetries": 3,
            "transactionId": None,
        },
        "states": {
            "idle": {
                "on": {
                    "INITIATE": [
                        {
                            "target": "validating",
                            "actions": [{"type": "setPaymentDetails"}],
                        }
                    ],
                }
            },
            "validating": {
                "always": [
                    {
                        "target": "idle",
                        "guard": "amountInvalid",
                        "actions": [{"type": "setAmountError"}],
                    },
                    {"target": "authorizing", "actions": []},
                ]
            },
            "authorizing": {
                "invoke": {
                    "src": "authorizePayment",
                    "onDone": [
                        {
                            "target": "capturing",
                            "guard": "authorizationApproved",
                            "actions": [{"type": "storeAuthCode"}],
                        },
                        {
                            "target": "declined",
                            "actions": [{"type": "storeDeclineReason"}],
                        },
                    ],
                    "onError": [
                        {
                            "target": "retrying",
                            "actions": [{"type": "logAuthError"}],
                        }
                    ],
                }
            },
            "retrying": {
                "always": [
                    {
                        "target": "failed",
                        "guard": "maxRetriesReached",
                        "actions": [],
                    },
                    {
                        "target": "authorizing",
                        "actions": [{"type": "incrementRetry"}],
                    },
                ]
            },
            "capturing": {
                "invoke": {
                    "src": "capturePayment",
                    "onDone": [
                        {
                            "target": "completed",
                            "actions": [{"type": "storeTransactionId"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "failed",
                            "actions": [{"type": "logCaptureError"}],
                        }
                    ],
                }
            },
            "declined": {
                "on": {
                    "RETRY_WITH_DIFFERENT_METHOD": [
                        {
                            "target": "idle",
                            "actions": [{"type": "clearPaymentDetails"}],
                        }
                    ],
                }
            },
            "completed": {
                "entry": {"type": "sendReceipt"},
                "type": "final",
            },
            "failed": {
                "entry": {"type": "notifyPaymentFailure"},
                "on": {
                    "RETRY": [
                        {
                            "target": "idle",
                            "actions": [{"type": "resetRetries"}],
                        }
                    ],
                },
            },
        },
    },
    # ===================================================================
    # 15. estateWizard — Multi-step wizard with nested states, guards
    # ===================================================================
    "estateWizard": {
        "id": "estateWizard",
        "initial": "propertyDetails",
        "context": {
            "propertyType": None,
            "address": None,
            "price": None,
            "photos": [],
            "listingId": None,
        },
        "states": {
            "propertyDetails": {
                "initial": "editing",
                "states": {
                    "editing": {
                        "on": {
                            "NEXT": [
                                {
                                    "target": "validating",
                                    "actions": [
                                        {"type": "capturePropertyDetails"}
                                    ],
                                }
                            ],
                        }
                    },
                    "validating": {
                        "always": [
                            {
                                "target": "#estateWizard.addressEntry",
                                "guard": "propertyDetailsValid",
                                "actions": [],
                            },
                            {
                                "target": "editing",
                                "actions": [{"type": "showPropertyErrors"}],
                            },
                        ]
                    },
                },
            },
            "addressEntry": {
                "on": {
                    "NEXT": [
                        {
                            "target": "pricing",
                            "guard": "addressValid",
                            "actions": [{"type": "captureAddress"}],
                        }
                    ],
                    "BACK": [{"target": "propertyDetails", "actions": []}],
                }
            },
            "pricing": {
                "on": {
                    "NEXT": [
                        {
                            "target": "photoUpload",
                            "guard": "priceValid",
                            "actions": [{"type": "capturePrice"}],
                        }
                    ],
                    "BACK": [{"target": "addressEntry", "actions": []}],
                }
            },
            "photoUpload": {
                "on": {
                    "UPLOAD": [{"target": "uploading", "actions": []}],
                    "SKIP": [{"target": "review", "actions": []}],
                    "BACK": [{"target": "pricing", "actions": []}],
                }
            },
            "uploading": {
                "invoke": {
                    "src": "uploadPhotos",
                    "onDone": [
                        {
                            "target": "review",
                            "actions": [{"type": "storePhotoUrls"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "photoUpload",
                            "actions": [{"type": "showUploadError"}],
                        }
                    ],
                }
            },
            "review": {
                "on": {
                    "SUBMIT": [{"target": "publishing", "actions": []}],
                    "BACK": [{"target": "photoUpload", "actions": []}],
                }
            },
            "publishing": {
                "invoke": {
                    "src": "publishListing",
                    "onDone": [
                        {
                            "target": "published",
                            "actions": [{"type": "storeListingId"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "review",
                            "actions": [{"type": "showPublishError"}],
                        }
                    ],
                }
            },
            "published": {
                "entry": {"type": "showSuccessConfirmation"},
                "type": "final",
            },
        },
    },
    # ===================================================================
    # 16. order — Order lifecycle with invoke
    # ===================================================================
    "order": {
        "id": "order",
        "initial": "created",
        "context": {"orderId": None, "items": [], "trackingNumber": None},
        "states": {
            "created": {
                "entry": {"type": "generateOrderId"},
                "on": {
                    "PAY": [{"target": "paymentProcessing", "actions": []}],
                    "CANCEL": [
                        {
                            "target": "cancelled",
                            "actions": [{"type": "logCancellation"}],
                        }
                    ],
                },
            },
            "paymentProcessing": {
                "invoke": {
                    "src": "processOrderPayment",
                    "onDone": [
                        {
                            "target": "paid",
                            "actions": [{"type": "storePaymentConfirmation"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "paymentFailed",
                            "actions": [{"type": "storePaymentError"}],
                        }
                    ],
                }
            },
            "paymentFailed": {
                "on": {
                    "RETRY_PAYMENT": [
                        {"target": "paymentProcessing", "actions": []}
                    ],
                    "CANCEL": [{"target": "cancelled", "actions": []}],
                }
            },
            "paid": {
                "on": {
                    "SHIP": [
                        {
                            "target": "shipping",
                            "actions": [{"type": "assignTrackingNumber"}],
                        }
                    ],
                    "REFUND": [{"target": "refunding", "actions": []}],
                }
            },
            "shipping": {
                "invoke": {
                    "src": "createShipment",
                    "onDone": [
                        {
                            "target": "shipped",
                            "actions": [{"type": "sendShippingNotification"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "paid",
                            "actions": [{"type": "logShippingError"}],
                        }
                    ],
                }
            },
            "shipped": {
                "on": {
                    "DELIVER": [{"target": "delivered", "actions": []}],
                    "RETURN_REQUESTED": [
                        {"target": "returnRequested", "actions": []}
                    ],
                }
            },
            "delivered": {
                "entry": {"type": "sendDeliveryConfirmation"},
                "on": {
                    "RETURN_REQUESTED": [
                        {"target": "returnRequested", "actions": []}
                    ],
                },
            },
            "returnRequested": {
                "on": {
                    "APPROVE_RETURN": [{"target": "refunding", "actions": []}],
                    "DENY_RETURN": [
                        {
                            "target": "delivered",
                            "actions": [{"type": "sendDenialNotice"}],
                        }
                    ],
                }
            },
            "refunding": {
                "invoke": {
                    "src": "processRefund",
                    "onDone": [
                        {
                            "target": "refunded",
                            "actions": [{"type": "sendRefundConfirmation"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "paid",
                            "actions": [{"type": "logRefundError"}],
                        }
                    ],
                }
            },
            "refunded": {"type": "final"},
            "cancelled": {"type": "final"},
        },
    },
    # ===================================================================
    # 17. dragFeature — Drag and drop states
    # ===================================================================
    "dragFeature": {
        "id": "dragFeature",
        "initial": "idle",
        "context": {
            "dragData": None,
            "dropTarget": None,
            "startPosition": None,
        },
        "states": {
            "idle": {
                "on": {
                    "MOUSE_DOWN": [
                        {
                            "target": "pointerDown",
                            "actions": [{"type": "captureStartPosition"}],
                        }
                    ],
                }
            },
            "pointerDown": {
                "on": {
                    "MOUSE_MOVE": [
                        {
                            "target": "dragging",
                            "guard": "movedBeyondThreshold",
                            "actions": [{"type": "initDrag"}],
                        }
                    ],
                    "MOUSE_UP": [{"target": "idle", "actions": []}],
                },
                "after": {"200": [{"target": "idle", "actions": []}]},
            },
            "dragging": {
                "entry": {"type": "showDragGhost"},
                "exit": {"type": "hideDragGhost"},
                "on": {
                    "MOUSE_MOVE": [
                        {
                            "target": "dragging",
                            "actions": [{"type": "updatePosition"}],
                        }
                    ],
                    "ENTER_DROP_ZONE": [
                        {
                            "target": "overDropZone",
                            "actions": [{"type": "highlightDropZone"}],
                        }
                    ],
                    "MOUSE_UP": [
                        {"target": "idle", "actions": [{"type": "cancelDrag"}]}
                    ],
                    "ESCAPE": [
                        {"target": "idle", "actions": [{"type": "cancelDrag"}]}
                    ],
                },
            },
            "overDropZone": {
                "entry": {"type": "showDropIndicator"},
                "exit": {"type": "hideDropIndicator"},
                "on": {
                    "MOUSE_MOVE": [
                        {
                            "target": "overDropZone",
                            "actions": [{"type": "updatePosition"}],
                        }
                    ],
                    "LEAVE_DROP_ZONE": [{"target": "dragging", "actions": []}],
                    "MOUSE_UP": [
                        {
                            "target": "dropped",
                            "actions": [{"type": "executeDrop"}],
                        }
                    ],
                    "ESCAPE": [
                        {"target": "idle", "actions": [{"type": "cancelDrag"}]}
                    ],
                },
            },
            "dropped": {
                "entry": {"type": "animateDropSuccess"},
                "after": {
                    "300": [
                        {
                            "target": "idle",
                            "actions": [{"type": "cleanupDrag"}],
                        }
                    ]
                },
            },
        },
    },
    # ===================================================================
    # 18. photoUploads — Upload flow with invoke, progress tracking
    # ===================================================================
    "photoUploads": {
        "id": "photoUploads",
        "initial": "idle",
        "context": {
            "files": [],
            "uploadedUrls": [],
            "currentIndex": 0,
            "error": None,
        },
        "states": {
            "idle": {
                "on": {
                    "SELECT_FILES": [
                        {
                            "target": "previewing",
                            "actions": [{"type": "setFiles"}],
                        }
                    ],
                }
            },
            "previewing": {
                "on": {
                    "REMOVE_FILE": [
                        {
                            "target": "previewing",
                            "actions": [{"type": "removeFile"}],
                        }
                    ],
                    "START_UPLOAD": [
                        {
                            "target": "uploading",
                            "guard": "hasFiles",
                            "actions": [{"type": "resetUploadState"}],
                        }
                    ],
                    "CANCEL": [
                        {"target": "idle", "actions": [{"type": "clearFiles"}]}
                    ],
                }
            },
            "uploading": {
                "invoke": {
                    "src": "uploadSingleFile",
                    "onDone": [
                        {
                            "target": "checkingProgress",
                            "actions": [{"type": "storeUploadedUrl"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "uploadError",
                            "actions": [{"type": "setUploadError"}],
                        }
                    ],
                }
            },
            "checkingProgress": {
                "always": [
                    {
                        "target": "complete",
                        "guard": "allFilesUploaded",
                        "actions": [],
                    },
                    {
                        "target": "uploading",
                        "actions": [{"type": "advanceIndex"}],
                    },
                ]
            },
            "uploadError": {
                "on": {
                    "RETRY": [
                        {
                            "target": "uploading",
                            "actions": [{"type": "clearError"}],
                        }
                    ],
                    "SKIP": [
                        {
                            "target": "checkingProgress",
                            "actions": [{"type": "advanceIndex"}],
                        }
                    ],
                    "CANCEL": [
                        {"target": "idle", "actions": [{"type": "clearFiles"}]}
                    ],
                }
            },
            "complete": {
                "entry": {"type": "showUploadSummary"},
                "on": {
                    "DONE": [
                        {"target": "idle", "actions": [{"type": "clearFiles"}]}
                    ],
                    "UPLOAD_MORE": [{"target": "idle", "actions": []}],
                },
            },
        },
    },
    # ===================================================================
    # 19. mcBookingRequest — Booking request with parallel approval
    # ===================================================================
    "mcBookingRequest": {
        "id": "mcBookingRequest",
        "initial": "submitted",
        "context": {"requestId": None, "venue": None, "date": None},
        "states": {
            "submitted": {
                "entry": {"type": "notifyApprovers"},
                "on": {
                    "START_REVIEW": [{"target": "underReview", "actions": []}],
                    "AUTO_REJECT": [
                        {
                            "target": "rejected",
                            "guard": "isBlackoutDate",
                            "actions": [{"type": "setAutoRejectReason"}],
                        }
                    ],
                },
            },
            "underReview": {
                "type": "parallel",
                "states": {
                    "venueApproval": {
                        "initial": "pending",
                        "states": {
                            "pending": {
                                "on": {
                                    "APPROVE_VENUE": [
                                        {"target": "approved", "actions": []}
                                    ],
                                    "REJECT_VENUE": [
                                        {"target": "rejected", "actions": []}
                                    ],
                                }
                            },
                            "approved": {},
                            "rejected": {},
                        },
                    },
                    "budgetApproval": {
                        "initial": "pending",
                        "states": {
                            "pending": {
                                "on": {
                                    "APPROVE_BUDGET": [
                                        {"target": "approved", "actions": []}
                                    ],
                                    "REJECT_BUDGET": [
                                        {"target": "rejected", "actions": []}
                                    ],
                                }
                            },
                            "approved": {},
                            "rejected": {},
                        },
                    },
                    "scheduleApproval": {
                        "initial": "pending",
                        "states": {
                            "pending": {
                                "on": {
                                    "APPROVE_SCHEDULE": [
                                        {"target": "approved", "actions": []}
                                    ],
                                    "REJECT_SCHEDULE": [
                                        {"target": "rejected", "actions": []}
                                    ],
                                }
                            },
                            "approved": {},
                            "rejected": {},
                        },
                    },
                },
                "onDone": [{"target": "finalReview", "actions": []}],
            },
            "finalReview": {
                "always": [
                    {
                        "target": "approved",
                        "guard": "allApprovalsGranted",
                        "actions": [],
                    },
                    {
                        "target": "rejected",
                        "actions": [{"type": "collectRejectionReasons"}],
                    },
                ]
            },
            "approved": {
                "entry": {"type": "sendApprovalNotification"},
                "type": "final",
            },
            "rejected": {
                "entry": {"type": "sendRejectionNotification"},
                "on": {
                    "RESUBMIT": [
                        {
                            "target": "submitted",
                            "actions": [{"type": "clearRejection"}],
                        }
                    ],
                },
            },
        },
    },
    # ===================================================================
    # 20. parallelism — Pure parallel state example
    # ===================================================================
    "parallelism": {
        "id": "parallelism",
        "initial": "running",
        "states": {
            "running": {
                "type": "parallel",
                "states": {
                    "taskA": {
                        "initial": "pending",
                        "states": {
                            "pending": {
                                "on": {
                                    "START_A": [
                                        {
                                            "target": "inProgress",
                                            "actions": [{"type": "logStartA"}],
                                        }
                                    ],
                                }
                            },
                            "inProgress": {
                                "on": {
                                    "COMPLETE_A": [
                                        {
                                            "target": "done",
                                            "actions": [
                                                {"type": "logCompleteA"}
                                            ],
                                        }
                                    ],
                                    "FAIL_A": [
                                        {
                                            "target": "failed",
                                            "actions": [{"type": "logFailA"}],
                                        }
                                    ],
                                }
                            },
                            "done": {},
                            "failed": {
                                "on": {
                                    "RETRY_A": [
                                        {"target": "pending", "actions": []}
                                    ]
                                },
                            },
                        },
                    },
                    "taskB": {
                        "initial": "pending",
                        "states": {
                            "pending": {
                                "on": {
                                    "START_B": [
                                        {
                                            "target": "inProgress",
                                            "actions": [{"type": "logStartB"}],
                                        }
                                    ],
                                }
                            },
                            "inProgress": {
                                "on": {
                                    "COMPLETE_B": [
                                        {
                                            "target": "done",
                                            "actions": [
                                                {"type": "logCompleteB"}
                                            ],
                                        }
                                    ],
                                    "FAIL_B": [
                                        {
                                            "target": "failed",
                                            "actions": [{"type": "logFailB"}],
                                        }
                                    ],
                                }
                            },
                            "done": {},
                            "failed": {
                                "on": {
                                    "RETRY_B": [
                                        {"target": "pending", "actions": []}
                                    ]
                                },
                            },
                        },
                    },
                    "taskC": {
                        "initial": "pending",
                        "states": {
                            "pending": {
                                "on": {
                                    "START_C": [
                                        {
                                            "target": "inProgress",
                                            "actions": [{"type": "logStartC"}],
                                        }
                                    ],
                                }
                            },
                            "inProgress": {
                                "on": {
                                    "COMPLETE_C": [
                                        {
                                            "target": "done",
                                            "actions": [
                                                {"type": "logCompleteC"}
                                            ],
                                        }
                                    ],
                                }
                            },
                            "done": {},
                        },
                    },
                },
            },
        },
    },
    # ===================================================================
    # 21. token — Token lifecycle with refresh invoke
    # ===================================================================
    "token": {
        "id": "token",
        "initial": "noToken",
        "context": {
            "accessToken": None,
            "refreshToken": None,
            "expiresAt": None,
        },
        "states": {
            "noToken": {
                "on": {
                    "LOGIN": [{"target": "authenticating", "actions": []}],
                }
            },
            "authenticating": {
                "invoke": {
                    "src": "loginService",
                    "onDone": [
                        {
                            "target": "active",
                            "actions": [{"type": "storeTokens"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "noToken",
                            "actions": [{"type": "showLoginError"}],
                        }
                    ],
                }
            },
            "active": {
                "entry": {"type": "scheduleRefresh"},
                "on": {
                    "TOKEN_EXPIRING": [
                        {"target": "refreshing", "actions": []}
                    ],
                    "LOGOUT": [
                        {
                            "target": "noToken",
                            "actions": [{"type": "clearTokens"}],
                        }
                    ],
                    "API_401": [{"target": "refreshing", "actions": []}],
                },
            },
            "refreshing": {
                "invoke": {
                    "src": "refreshTokenService",
                    "onDone": [
                        {
                            "target": "active",
                            "actions": [{"type": "storeTokens"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "noToken",
                            "actions": [
                                {"type": "clearTokens"},
                                {"type": "redirectToLogin"},
                            ],
                        }
                    ],
                }
            },
        },
    },
    # ===================================================================
    # 22. wizardForm — Generic wizard with validation guards
    # ===================================================================
    "wizardForm": {
        "id": "wizardForm",
        "initial": "intro",
        "context": {"formData": {}, "currentStep": 0, "totalSteps": 4},
        "states": {
            "intro": {
                "description": "Welcome screen explaining the wizard process.",
                "on": {
                    "BEGIN": [
                        {
                            "target": "step1",
                            "actions": [{"type": "initFormData"}],
                        }
                    ],
                },
            },
            "step1": {
                "entry": {"type": "loadStep1Data"},
                "on": {
                    "NEXT": [
                        {
                            "target": "step2",
                            "guard": "step1Valid",
                            "actions": [{"type": "saveStep1"}],
                        }
                    ],
                    "CANCEL": [{"target": "cancelled", "actions": []}],
                },
            },
            "step2": {
                "entry": {"type": "loadStep2Data"},
                "on": {
                    "NEXT": [
                        {
                            "target": "step3",
                            "guard": "step2Valid",
                            "actions": [{"type": "saveStep2"}],
                        }
                    ],
                    "BACK": [{"target": "step1", "actions": []}],
                    "CANCEL": [{"target": "cancelled", "actions": []}],
                },
            },
            "step3": {
                "entry": {"type": "loadStep3Data"},
                "on": {
                    "NEXT": [
                        {
                            "target": "step4",
                            "guard": "step3Valid",
                            "actions": [{"type": "saveStep3"}],
                        }
                    ],
                    "BACK": [{"target": "step2", "actions": []}],
                    "CANCEL": [{"target": "cancelled", "actions": []}],
                },
            },
            "step4": {
                "entry": {"type": "loadStep4Data"},
                "on": {
                    "SUBMIT": [
                        {
                            "target": "submitting",
                            "guard": "step4Valid",
                            "actions": [{"type": "saveStep4"}],
                        }
                    ],
                    "BACK": [{"target": "step3", "actions": []}],
                    "CANCEL": [{"target": "cancelled", "actions": []}],
                },
            },
            "submitting": {
                "invoke": {
                    "src": "submitWizard",
                    "onDone": [
                        {
                            "target": "success",
                            "actions": [{"type": "showCompletionMessage"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "step4",
                            "actions": [{"type": "showSubmitError"}],
                        }
                    ],
                }
            },
            "success": {"type": "final"},
            "cancelled": {
                "entry": {"type": "cleanupFormData"},
                "type": "final",
            },
        },
    },
    # ===================================================================
    # 23. authStateMachineSimple — Auth with context, invoke, guards
    # ===================================================================
    "authStateMachineSimple": {
        "id": "authStateMachineSimple",
        "initial": "unauthenticated",
        "context": {"user": None, "error": None, "token": None},
        "states": {
            "unauthenticated": {
                "entry": {"type": "clearAuthData"},
                "on": {
                    "LOGIN": [
                        {
                            "target": "loggingIn",
                            "actions": [{"type": "clearError"}],
                        }
                    ],
                    "SIGNUP": [
                        {
                            "target": "signingUp",
                            "actions": [{"type": "clearError"}],
                        }
                    ],
                },
            },
            "loggingIn": {
                "invoke": {
                    "src": "loginAPI",
                    "onDone": [
                        {
                            "target": "authenticated",
                            "actions": [
                                {"type": "setUser"},
                                {"type": "setToken"},
                            ],
                        }
                    ],
                    "onError": [
                        {
                            "target": "unauthenticated",
                            "actions": [{"type": "setError"}],
                        }
                    ],
                }
            },
            "signingUp": {
                "invoke": {
                    "src": "signupAPI",
                    "onDone": [
                        {
                            "target": "authenticated",
                            "actions": [
                                {"type": "setUser"},
                                {"type": "setToken"},
                            ],
                        }
                    ],
                    "onError": [
                        {
                            "target": "unauthenticated",
                            "actions": [{"type": "setError"}],
                        }
                    ],
                }
            },
            "authenticated": {
                "on": {
                    "LOGOUT": [
                        {
                            "target": "unauthenticated",
                            "actions": [{"type": "clearAuthData"}],
                        }
                    ],
                    "REFRESH_TOKEN": [
                        {"target": "refreshingToken", "actions": []}
                    ],
                    "DELETE_ACCOUNT": [
                        {
                            "target": "deletingAccount",
                            "guard": "isConfirmed",
                            "actions": [],
                        }
                    ],
                }
            },
            "refreshingToken": {
                "invoke": {
                    "src": "refreshTokenAPI",
                    "onDone": [
                        {
                            "target": "authenticated",
                            "actions": [{"type": "setToken"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "unauthenticated",
                            "actions": [
                                {"type": "clearAuthData"},
                                {"type": "setError"},
                            ],
                        }
                    ],
                }
            },
            "deletingAccount": {
                "invoke": {
                    "src": "deleteAccountAPI",
                    "onDone": [
                        {
                            "target": "accountDeleted",
                            "actions": [{"type": "clearAuthData"}],
                        }
                    ],
                    "onError": [
                        {
                            "target": "authenticated",
                            "actions": [{"type": "setError"}],
                        }
                    ],
                }
            },
            "accountDeleted": {
                "entry": {"type": "showDeletionConfirmation"},
                "type": "final",
            },
        },
    },
    # ===================================================================
    # 24. thermoValve — IoT valve controller with temperature guards
    # ===================================================================
    "thermoValve": {
        "id": "thermoValve",
        "initial": "off",
        "context": {"temperature": 20, "setPoint": 22, "hysteresis": 1},
        "states": {
            "off": {
                "description": "Valve is closed. Heating is off.",
                "entry": {"type": "closeValve"},
                "on": {
                    "ENABLE": [
                        {
                            "target": "monitoring",
                            "actions": [{"type": "logEnable"}],
                        }
                    ],
                },
            },
            "monitoring": {
                "description": "Reading sensor and deciding whether to heat.",
                "always": [
                    {
                        "target": "heating",
                        "guard": "temperatureBelowSetPoint",
                        "actions": [],
                    },
                    {
                        "target": "cooling",
                        "guard": "temperatureAboveSetPoint",
                        "actions": [],
                    },
                ],
                "on": {
                    "DISABLE": [
                        {"target": "off", "actions": [{"type": "logDisable"}]}
                    ],
                    "SENSOR_UPDATE": [
                        {
                            "target": "monitoring",
                            "actions": [{"type": "updateTemperature"}],
                        }
                    ],
                },
            },
            "heating": {
                "entry": {"type": "openValve"},
                "on": {
                    "SENSOR_UPDATE": [
                        {
                            "target": "monitoring",
                            "guard": "temperatureReachedSetPoint",
                            "actions": [{"type": "updateTemperature"}],
                        },
                        {
                            "target": "heating",
                            "actions": [{"type": "updateTemperature"}],
                        },
                    ],
                    "DISABLE": [
                        {"target": "off", "actions": [{"type": "logDisable"}]}
                    ],
                    "OVERHEAT": [
                        {
                            "target": "emergency",
                            "actions": [{"type": "logOverheat"}],
                        }
                    ],
                },
            },
            "cooling": {
                "entry": {"type": "closeValve"},
                "on": {
                    "SENSOR_UPDATE": [
                        {
                            "target": "monitoring",
                            "guard": "temperatureDroppedBelowHysteresis",
                            "actions": [{"type": "updateTemperature"}],
                        },
                        {
                            "target": "cooling",
                            "actions": [{"type": "updateTemperature"}],
                        },
                    ],
                    "DISABLE": [
                        {"target": "off", "actions": [{"type": "logDisable"}]}
                    ],
                },
            },
            "emergency": {
                "entry": {"type": "emergencyShutdown"},
                "on": {
                    "RESET": [
                        {
                            "target": "off",
                            "actions": [{"type": "clearEmergency"}],
                        }
                    ],
                },
            },
        },
    },
    # ===================================================================
    # 25. cronometro — Simple stopwatch with running/paused/reset
    # ===================================================================
    "cronometro": {
        "id": "cronometro",
        "initial": "stopped",
        "context": {"elapsed": 0, "laps": []},
        "states": {
            "stopped": {
                "description": "Stopwatch is not running.",
                "entry": {"type": "displayZero"},
                "on": {
                    "START": [
                        {
                            "target": "running",
                            "actions": [{"type": "resetElapsed"}],
                        }
                    ],
                },
            },
            "running": {
                "entry": {"type": "startInterval"},
                "exit": {"type": "stopInterval"},
                "on": {
                    "PAUSE": [{"target": "paused", "actions": []}],
                    "LAP": [
                        {
                            "target": "running",
                            "actions": [{"type": "recordLap"}],
                        }
                    ],
                    "RESET": [
                        {
                            "target": "stopped",
                            "actions": [
                                {"type": "resetElapsed"},
                                {"type": "clearLaps"},
                            ],
                        }
                    ],
                    "TICK": [
                        {
                            "target": "running",
                            "actions": [{"type": "incrementElapsed"}],
                        }
                    ],
                },
            },
            "paused": {
                "on": {
                    "RESUME": [{"target": "running", "actions": []}],
                    "RESET": [
                        {
                            "target": "stopped",
                            "actions": [
                                {"type": "resetElapsed"},
                                {"type": "clearLaps"},
                            ],
                        }
                    ],
                    "LAP": [
                        {
                            "target": "paused",
                            "actions": [{"type": "recordLap"}],
                        }
                    ],
                }
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


class StatelyRealTests(unittest.TestCase):
    """25 machines x 5 templates = 125 tests (log=True, file_count=2)."""

    _tmp_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="xsm_stately_"))

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


# --- register 125 tests: log=True, file_count=2 ---
for _mid, _cfg in STATELY_MACHINES.items():
    for _tpl in TEMPLATES:
        _fn = _make_test(_mid, _cfg, _tpl, log=True, file_count=2)
        setattr(StatelyRealTests, _fn.__name__, _fn)


# ---------------------------------------------------------------------------
# Test class 2: log=False, file_count=2 (historically bug-prone)
# ---------------------------------------------------------------------------


class StatelyRealTestsLogFalse(unittest.TestCase):
    """25 machines x 5 templates = 125 tests (log=False, file_count=2)."""

    _tmp_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="xsm_stately_nolog_"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)


for _mid, _cfg in STATELY_MACHINES.items():
    for _tpl in TEMPLATES:
        _fn = _make_test(_mid, _cfg, _tpl, log=False, file_count=2)
        setattr(StatelyRealTestsLogFalse, _fn.__name__, _fn)


# ---------------------------------------------------------------------------
# Test class 3: log=True, file_count=1 (merged files — most complex path)
# ---------------------------------------------------------------------------


class StatelyRealTestsSingleFile(unittest.TestCase):
    """25 machines x 5 templates = 125 tests (log=True, file_count=1)."""

    _tmp_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="xsm_stately_fc1_"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)


for _mid, _cfg in STATELY_MACHINES.items():
    for _tpl in TEMPLATES:
        _fn = _make_test(_mid, _cfg, _tpl, log=True, file_count=1)
        setattr(StatelyRealTestsSingleFile, _fn.__name__, _fn)
