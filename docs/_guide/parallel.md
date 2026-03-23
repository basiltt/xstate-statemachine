---
title: "Parallel States"
description: "Concurrent state regions — multiple independent processes running simultaneously."
---

Parallel states model **concurrent activity** — multiple independent processes running at the same time within the same machine. Instead of being in one child state at a time (like compound states), a parallel state is in **all** of its child regions simultaneously.

## What Are Parallel States?

In a compound state, the machine is in exactly one child at a time. In a **parallel** state, the machine is in one state from _every_ child region at the same time. Each region operates independently — events are delivered to all regions, and each region handles them according to its own transitions.

```
┌─────────────── playing (parallel) ───────────────┐
│                                                   │
│  ┌── video ──┐  ┌── audio ──┐  ┌── controls ──┐  │
│  │  loading  │  │   muted   │  │   visible    │  │
│  │  showing  │  │  playing  │  │   hidden     │  │
│  │ buffering │  └───────────┘  └──────────────┘  │
│  └───────────┘                                    │
│                                                   │
│  ALL regions are active simultaneously            │
└───────────────────────────────────────────────────┘
```

## JSON Example: Media Player

```json
{
  "id": "mediaPlayer",
  "initial": "playing",
  "states": {
    "playing": {
      "type": "parallel",
      "states": {
        "video": {
          "initial": "loading",
          "states": {
            "loading":   {"on": {"VIDEO_LOADED": "showing"}},
            "showing":   {"on": {"BUFFER": "buffering"}},
            "buffering": {"on": {"VIDEO_LOADED": "showing"}}
          }
        },
        "audio": {
          "initial": "muted",
          "states": {
            "muted":   {"on": {"UNMUTE": "playing"}},
            "playing": {"on": {"MUTE": "muted"}}
          }
        },
        "controls": {
          "initial": "visible",
          "states": {
            "visible": {"after": {"3000": "hidden"}},
            "hidden":  {"on": {"MOUSE_MOVE": "visible"}}
          }
        }
      }
    }
  }
}
```

Running it:

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "mediaPlayer",
    "initial": "playing",
    "states": {
        "playing": {
            "type": "parallel",
            "states": {
                "video": {
                    "initial": "loading",
                    "states": {
                        "loading":   {"on": {"VIDEO_LOADED": "showing"}},
                        "showing":   {"on": {"BUFFER": "buffering"}},
                        "buffering": {"on": {"VIDEO_LOADED": "showing"}}
                    }
                },
                "audio": {
                    "initial": "muted",
                    "states": {
                        "muted":   {"on": {"UNMUTE": "playing"}},
                        "playing": {"on": {"MUTE": "muted"}}
                    }
                },
                "controls": {
                    "initial": "visible",
                    "states": {
                        "visible": {"after": {"3000": "hidden"}},
                        "hidden":  {"on": {"MOUSE_MOVE": "visible"}}
                    }
                }
            }
        }
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'mediaPlayer.playing.video.loading',
#  'mediaPlayer.playing.audio.muted',
#  'mediaPlayer.playing.controls.visible'}

# Events target specific regions independently
interp.send("VIDEO_LOADED")
print(interp.active_state_ids)
# {'mediaPlayer.playing.video.showing',
#  'mediaPlayer.playing.audio.muted',
#  'mediaPlayer.playing.controls.visible'}

interp.send("UNMUTE")
print(interp.active_state_ids)
# {'mediaPlayer.playing.video.showing',
#  'mediaPlayer.playing.audio.playing',
#  'mediaPlayer.playing.controls.visible'}

interp.stop()
```

All three regions (`video`, `audio`, `controls`) are active at the same time. Sending `VIDEO_LOADED` only affects the `video` region — the other regions stay in their current states.

## How It Works

When the machine enters a parallel state:

1. **All** child regions are activated simultaneously
2. Each region enters its own `initial` child state
3. Events are delivered to **every** region
4. Each region handles (or ignores) the event independently
5. `active_state_ids` shows one active state from each region

> **Note:** Parallel regions don't have an `initial` flag on the parent — there's no "first" child. All children start together. However, each region (which is a compound state) still needs its own `initial` child.

## Creating Parallel States

### JSON: `"type": "parallel"`

```json
{
  "myParallelState": {
    "type": "parallel",
    "states": {
      "regionA": {
        "initial": "idle",
        "states": {
          "idle": {"on": {"START_A": "running"}},
          "running": {"on": {"STOP_A": "idle"}}
        }
      },
      "regionB": {
        "initial": "idle",
        "states": {
          "idle": {"on": {"START_B": "running"}},
          "running": {"on": {"STOP_B": "idle"}}
        }
      }
    }
  }
}
```

### Pythonic: `parallel=True` Parameter

```python
from xstate_statemachine import State, StateMachine, SyncInterpreter

class PlayerMachine(StateMachine):
    machine_id = "player"

    playing = State("playing", initial=True, parallel=True, states=[
        State("video", states=[
            State("loading", initial=True, on={"VIDEO_LOADED": "showing"}),
            State("showing"),
        ]),
        State("audio", states=[
            State("muted", initial=True, on={"UNMUTE": "playing"}),
            State("playing", on={"MUTE": "muted"}),
        ]),
    ])

machine = PlayerMachine.create_machine()
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'player.playing.video.loading', 'player.playing.audio.muted'}

interp.send("VIDEO_LOADED")
interp.send("UNMUTE")
print(interp.active_state_ids)
# {'player.playing.video.showing', 'player.playing.audio.playing'}

interp.stop()
```

> **Warning:** Children of a parallel state should **not** have `initial=True`. All children of a parallel parent are entered simultaneously. Setting `initial=True` on a parallel child will raise an `InvalidConfigError`.

### MachineBuilder: `.child_states(parent, parallel=True)`

```python
from xstate_statemachine import MachineBuilder, SyncInterpreter

machine = (
    MachineBuilder("player")
    .state("playing", initial=True)
    .child_states("playing", parallel=True, states={
        "video": {
            "initial": "loading",
            "states": {
                "loading": {"on": {"VIDEO_LOADED": "showing"}},
                "showing": {}
            }
        },
        "audio": {
            "initial": "muted",
            "states": {
                "muted":   {"on": {"UNMUTE": "playing"}},
                "playing": {"on": {"MUTE": "muted"}}
            }
        }
    })
    .build()
)

interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'player.playing.video.loading', 'player.playing.audio.muted'}

interp.stop()
```

### Functional API

```python
from xstate_statemachine import State, build_machine, SyncInterpreter

playing = State("playing", initial=True, parallel=True, states=[
    State("video", states=[
        State("loading", initial=True, on={"VIDEO_LOADED": "showing"}),
        State("showing"),
    ]),
    State("audio", states=[
        State("muted", initial=True, on={"UNMUTE": "playing"}),
        State("playing", on={"MUTE": "muted"}),
    ]),
])

machine = build_machine(id="player", states=[playing])
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'player.playing.video.loading', 'player.playing.audio.muted'}

interp.stop()
```

## Multiple Regions Example (3+ Regions)

A game state with independent physics, AI, and UI regions:

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "game",
    "initial": "running",
    "states": {
        "running": {
            "type": "parallel",
            "states": {
                "physics": {
                    "initial": "simulating",
                    "states": {
                        "simulating": {"on": {"PAUSE_PHYSICS": "paused"}},
                        "paused": {"on": {"RESUME_PHYSICS": "simulating"}}
                    }
                },
                "ai": {
                    "initial": "thinking",
                    "states": {
                        "thinking": {"on": {"AI_DECIDED": "executing"}},
                        "executing": {"on": {"AI_DONE": "thinking"}}
                    }
                },
                "rendering": {
                    "initial": "drawing",
                    "states": {
                        "drawing": {"on": {"FRAME_DONE": "waiting"}},
                        "waiting": {"on": {"VSYNC": "drawing"}}
                    }
                }
            },
            "on": {
                "QUIT": "gameOver"
            }
        },
        "gameOver": {
            "type": "final"
        }
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'game.running.physics.simulating',
#  'game.running.ai.thinking',
#  'game.running.rendering.drawing'}

# Each region transitions independently
interp.send("PAUSE_PHYSICS")
interp.send("AI_DECIDED")

print(interp.active_state_ids)
# {'game.running.physics.paused',
#  'game.running.ai.executing',
#  'game.running.rendering.drawing'}

# Parent transition exits ALL regions at once
interp.send("QUIT")
print(interp.active_state_ids)
# {'game.gameOver'}

interp.stop()
```

> **Tip:** The `QUIT` event is on the parent parallel state `running`. It catches the event from **any** combination of region states and exits them all, transitioning to `gameOver`.

## Parallel with Actions

Entry and exit actions fire when parallel regions are entered or exited:

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "withActions",
    "initial": "active",
    "states": {
        "active": {
            "type": "parallel",
            "entry": "logParallelEntry",
            "exit":  "logParallelExit",
            "states": {
                "regionA": {
                    "initial": "idle",
                    "entry": "initRegionA",
                    "states": {
                        "idle": {"on": {"GO_A": "running"}},
                        "running": {}
                    }
                },
                "regionB": {
                    "initial": "idle",
                    "entry": "initRegionB",
                    "states": {
                        "idle": {"on": {"GO_B": "running"}},
                        "running": {}
                    }
                }
            },
            "on": {"SHUTDOWN": "stopped"}
        },
        "stopped": {"type": "final"}
    }
}

class ParallelLogic(MachineLogic):
    def logParallelEntry(self, interpreter, context, event, action_def):
        print("Entered parallel state")

    def logParallelExit(self, interpreter, context, event, action_def):
        print("Exiting parallel state — all regions stopping")

    def initRegionA(self, interpreter, context, event, action_def):
        print("Region A initialized")

    def initRegionB(self, interpreter, context, event, action_def):
        print("Region B initialized")

machine = create_machine(config, logic=ParallelLogic())
interp = SyncInterpreter(machine).start()
# Output:
# Entered parallel state
# Region A initialized
# Region B initialized

interp.send("SHUTDOWN")
# Output:
# Exiting parallel state — all regions stopping

interp.stop()
```

## Parallel with Guards

Guards work within parallel regions just like in any other state:

```json
{
  "dashboard": {
    "type": "parallel",
    "states": {
      "dataFeed": {
        "initial": "live",
        "states": {
          "live": {
            "on": {
              "REFRESH": [
                {"target": "refreshing", "guard": "isOnline"},
                {"actions": "showOfflineMessage"}
              ]
            }
          },
          "refreshing": {
            "on": {"DATA_LOADED": "live"}
          }
        }
      },
      "alerts": {
        "initial": "checking",
        "states": {
          "checking": {
            "on": {"ALERTS_LOADED": "displaying"}
          },
          "displaying": {}
        }
      }
    }
  }
}
```

## Parallel Containing Nested States

Parallel regions can themselves contain compound (nested) states — any combination of hierarchy is valid:

```python
from xstate_statemachine import create_machine, SyncInterpreter

config = {
    "id": "nestedParallel",
    "initial": "app",
    "states": {
        "app": {
            "type": "parallel",
            "states": {
                "navigation": {
                    "initial": "home",
                    "states": {
                        "home": {
                            "initial": "feed",
                            "states": {
                                "feed": {"on": {"VIEW_POST": "detail"}},
                                "detail": {"on": {"BACK": "feed"}}
                            }
                        },
                        "search": {"on": {"GO_HOME": "home"}}
                    },
                    "on": {"SEARCH": "search"}
                },
                "notifications": {
                    "initial": "idle",
                    "states": {
                        "idle": {"on": {"NEW_NOTIFICATION": "showing"}},
                        "showing": {
                            "after": {"5000": "idle"}
                        }
                    }
                }
            }
        }
    }
}

machine = create_machine(config)
interp = SyncInterpreter(machine).start()

print(interp.active_state_ids)
# {'nestedParallel.app.navigation.home.feed',
#  'nestedParallel.app.notifications.idle'}

interp.send("VIEW_POST")
print(interp.active_state_ids)
# {'nestedParallel.app.navigation.home.detail',
#  'nestedParallel.app.notifications.idle'}

# Notification arrives — only affects the notifications region
interp.send("NEW_NOTIFICATION")
print(interp.active_state_ids)
# {'nestedParallel.app.navigation.home.detail',
#  'nestedParallel.app.notifications.showing'}

interp.stop()
```

## active_state_ids with Parallel

When parallel states are active, `active_state_ids` contains **one leaf state from each active region**:

```python
interp = SyncInterpreter(machine).start()

# Flat machine: always one active state
# {'myMachine.someState'}

# Parallel machine: one per region
# {'myMachine.parallel.regionA.childA',
#  'myMachine.parallel.regionB.childB',
#  'myMachine.parallel.regionC.childC'}
```

You can check whether a specific region is in a specific state:

```python
active = interp.active_state_ids

# Is video currently showing?
video_showing = "mediaPlayer.playing.video.showing" in active

# Is any region in an error state?
has_error = any("error" in sid for sid in active)

# Which regions are active?
regions = {sid.split(".")[2] for sid in active if sid.count(".") >= 2}
```

## Complete Example: Dashboard with Notifications, Data Feed, and User Activity

```python
from xstate_statemachine import create_machine, SyncInterpreter, MachineLogic

config = {
    "id": "dashboard",
    "initial": "active",
    "context": {
        "notifications": [],
        "feedData": [],
        "lastActivity": None
    },
    "states": {
        "active": {
            "type": "parallel",
            "states": {
                "notifications": {
                    "initial": "polling",
                    "states": {
                        "polling": {
                            "invoke": {
                                "src": "fetchNotifications",
                                "onDone": {
                                    "target": "displaying",
                                    "actions": "storeNotifications"
                                },
                                "onError": "error"
                            }
                        },
                        "displaying": {
                            "after": {"30000": "polling"},
                            "on": {
                                "MARK_READ": {"actions": "markAsRead"},
                                "DISMISS_ALL": {"actions": "clearNotifications"}
                            }
                        },
                        "error": {
                            "after": {"60000": "polling"}
                        }
                    }
                },
                "dataFeed": {
                    "initial": "loading",
                    "states": {
                        "loading": {
                            "invoke": {
                                "src": "fetchFeedData",
                                "onDone": {
                                    "target": "live",
                                    "actions": "storeFeedData"
                                },
                                "onError": "stale"
                            }
                        },
                        "live": {
                            "after": {"15000": "loading"},
                            "on": {
                                "FORCE_REFRESH": "loading"
                            }
                        },
                        "stale": {
                            "after": {"30000": "loading"},
                            "on": {
                                "FORCE_REFRESH": "loading"
                            }
                        }
                    }
                },
                "userActivity": {
                    "initial": "active",
                    "states": {
                        "active": {
                            "after": {"300000": "idle"},
                            "on": {
                                "USER_ACTION": {
                                    "target": "active",
                                    "actions": "recordActivity"
                                }
                            }
                        },
                        "idle": {
                            "entry": "dimDisplay",
                            "on": {
                                "USER_ACTION": {
                                    "target": "active",
                                    "actions": "recordActivity"
                                }
                            }
                        }
                    }
                }
            },
            "on": {
                "LOGOUT": "loggedOut"
            }
        },
        "loggedOut": {
            "type": "final"
        }
    }
}

class DashboardLogic(MachineLogic):
    def fetchNotifications(self, interpreter, context, event):
        return [{"id": 1, "msg": "New message"}, {"id": 2, "msg": "Update"}]

    def storeNotifications(self, interpreter, context, event, action_def):
        context["notifications"] = event.data
        print(f"Loaded {len(event.data)} notifications")

    def markAsRead(self, interpreter, context, event, action_def):
        nid = event.data.get("id")
        context["notifications"] = [
            n for n in context["notifications"] if n.get("id") != nid
        ]

    def clearNotifications(self, interpreter, context, event, action_def):
        context["notifications"] = []

    def fetchFeedData(self, interpreter, context, event):
        return [{"metric": "cpu", "value": 42}, {"metric": "mem", "value": 78}]

    def storeFeedData(self, interpreter, context, event, action_def):
        context["feedData"] = event.data
        print(f"Feed updated with {len(event.data)} entries")

    def recordActivity(self, interpreter, context, event, action_def):
        import time
        context["lastActivity"] = time.time()

    def dimDisplay(self, interpreter, context, event, action_def):
        print("User idle — dimming display")

machine = create_machine(config, logic=DashboardLogic())
interp = SyncInterpreter(machine).start()

# All three regions start simultaneously
print(interp.active_state_ids)
# Shows one state from each of: notifications, dataFeed, userActivity

# User action resets the idle timer in userActivity,
# without affecting notifications or dataFeed
interp.send("USER_ACTION")

# Force refresh the data feed — only affects dataFeed region
interp.send("FORCE_REFRESH")

# Logout exits ALL regions at once
interp.send("LOGOUT")
print(interp.active_state_ids)
# {'dashboard.loggedOut'}

interp.stop()
```

This dashboard runs three completely independent processes:

- **Notifications:** polls every 30s, displays results, retries on error every 60s
- **Data Feed:** refreshes every 15s, falls back to stale mode on error
- **User Activity:** tracks idle time, dims the display after 5 minutes of inactivity

All three regions run concurrently, and a single `LOGOUT` event from the parent cleanly shuts them all down.
