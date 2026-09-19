# Video Script — "Stop Writing State. Start Drawing It."

**Runtime:** ~7 minutes · **Word count:** ~1,010 · **Pace:** ~145 wpm
**Purpose:** Top-of-funnel promo for `xstate-statemachine`, aimed at Python
developers including juniors.

> **Verification note.** Every terminal output in this script is copy-pasted
> from a real run against the published PyPI package `xstate-statemachine==0.7.0`
> in a clean virtualenv. Nothing here is written from memory or idealised. If you
> re-record, re-run the snippets in `scripts/` and paste fresh output rather than
> reusing these — a promo demo that fails on a viewer's machine costs more trust
> than no video at all.

---

## Diagram Reference

Diagrams are produced separately (see `VIDEO_DIAGRAMS.md` for the source JSON).
The script refers to them **only** by these labels.

| Label | Machine | Shows | First appears |
|---|---|---|---|
| **Diagram 1** | `trafficLight` | 3 states, `after` timers | [01:15] |
| **Diagram 2** | `checkout` | guards, `invoke`, final state | [00:35] |
| **Diagram 3** | `player` | two parallel regions | [04:30] |

**Diagram 2 is the hero image** — it appears three times ([00:35], [02:20],
[03:40]) and carries the core argument. Render it at the highest quality and
prepare three variants:

- **2a** — plain, all states neutral
- **2b** — `cartNotEmpty` guard label highlighted on the `cart → payment` arrow
- **2c** — `failure` state highlighted, with the `RETRY` arrow emphasised

---

## Scene 1 — The Hook

**[00:00 – 00:35]**

### VISUAL

Plain editor, dark theme. Type this out live, letting it grow visibly ugly:

```python
if is_loading and not has_error and payment_started and not cancelled:
    if retry_count < 3 and not already_charged:
        ...
```

Pause one beat on the finished mess. Then select all and **delete** — the whole
block vanishes to empty screen.

*No diagram in this scene.*

### VOICEOVER

> Every developer has written this function.
>
> Six booleans. Fourteen combinations you never tested. And somewhere in there,
> a bug where a user gets charged twice — because `payment_started` was `True`
> while `cancelled` was also `True`.
>
> That state was never supposed to exist. But nothing stopped it.
>
> What if that combination were literally impossible to reach? Not "we tested
> for it." Impossible.

---

## Scene 2 — The Reframe

**[00:35 – 01:15]**

### VISUAL

> **DIAGRAM 2 (variant 2a)** — fade in, centred, full frame.
> Animate the arrows drawing in one at a time over ~4 seconds, then hold static.

### VOICEOVER

> This is a statechart. Five boxes, a few arrows. You can read it in about ten
> seconds — and you already know how checkout works.
>
> Here's the idea: **this diagram is the code.** Not a doc that goes stale. Not
> a comment someone forgot. The actual, running program.
>
> That's `xstate-statemachine` — a Python library that turns diagrams like this
> into working software. And it's a genuinely different way to think about
> writing Python.
>
> You stop writing *how* the program moves between states. You describe *what
> the states are*. The library handles the rest.

---

## Scene 3 — Your First Machine

**[01:15 – 02:20]**

### VISUAL

Split screen throughout.

- **Left:** the JSON below, typed in
- **Right:** **DIAGRAM 1**, with the active state highlighted and cycling
  green → yellow → red in time with the narration

Open on the install command, full frame, ~2s:

```bash
pip install xstate-statemachine
```

Then the split. Left side shows `traffic_light.json`:

```json
{
  "id": "trafficLight",
  "initial": "green",
  "states": {
    "green":  { "after": { "3000": "yellow" } },
    "yellow": { "after": { "1000": "red" } },
    "red":    { "after": { "4000": "green" } }
  }
}
```

Then the Python:

```python
m = create_machine(json.load(open("traffic_light.json")), logic=MachineLogic())
i = Interpreter(m)
await i.start()
```

Cut to terminal. **Real output:**

```
t=0.0s : ['trafficLight.green']
t=3.2s : ['trafficLight.yellow']  <- no timer code written
t=4.2s : ['trafficLight.red']
```

> ⚠️ **Editor's note.** These are genuine 3-second and 1-second waits. Either
> speed the clip 2× or pre-record it — do not leave four seconds of dead air
> around [02:00].

### VOICEOVER

> Let's build something. A traffic light.
>
> Three states. Green waits three seconds, becomes yellow. Yellow waits one,
> becomes red. Red waits four, back to green.
>
> *(beat while the terminal output appears)*
>
> Look at what's *not* there. No `sleep` loop. No timer thread. No `while True`.
> No scheduling code at all.
>
> I described the timing. The library made it happen. That's the shift.

---

## Scene 4 — Guards: Rules That Can't Be Skipped

**[02:20 – 03:40]**

### VISUAL

> **DIAGRAM 2 (variant 2b)** — the `cartNotEmpty` guard label on the
> `cart → payment` arrow highlighted, ideally with a subtle pulse or glow.
> Hold for the first two sentences.

Then cut to code:

```python
def cart_not_empty(ctx, e): return ctx["items"] > 0
def can_retry(ctx, e):      return ctx["attempts"] < 3

logic = MachineLogic(
    guards={"cartNotEmpty": cart_not_empty, "canRetry": can_retry},
    services={"chargeCard": charge_card},
)
```

Cut to terminal. **Real output:**

```
empty cart, send CHECKOUT : ['checkout.cart']      <- guard blocked
2 items,   send CHECKOUT : ['checkout.success']    <- guard allowed
```

### VOICEOVER

> Now something real. Checkout.
>
> See the label on that arrow — `cartNotEmpty`? That's a **guard**. A rule
> attached to the transition itself.
>
> *(beat for the code)*
>
> Empty cart, send `CHECKOUT` — nothing happens. Not an exception. Not a crash.
> The transition simply isn't available.
>
> Two items — straight through payment to success.
>
> And here's the part I want junior developers to hear: **there is no path
> around that guard.** You can't forget the `if`. You can't call the wrong
> function. The rule lives on the arrow, so every route through that arrow
> obeys it.

---

## Scene 5 — Impossible States

**[03:40 – 04:30]**

### VISUAL

> **DIAGRAM 2 (variant 2c)** — `failure` state highlighted. As the narration
> reaches "I send `RETRY`", flash the `RETRY` arrow red briefly, then grey it
> out to signal it isn't reachable from `cart`.

Terminal alongside or below. **Real output:**

```
payment failed -> ['checkout.failure']
after CANCEL   -> ['checkout.cart']

Now the impossible part:
RETRY from cart-> ['checkout.cart']  <- ignored, not a crash
```

Close the scene by briefly cutting back to the deleted boolean mess from
Scene 1 — one second, as a callback.

### VOICEOVER

> The card gets declined — we land in `failure`. Cancel — back to the cart.
>
> Now watch. From the cart, I send `RETRY`. Retry a payment that isn't
> happening.
>
> Nothing. No crash, no exception, no corrupted state. The cart has no `RETRY`
> arrow, so the event is simply ignored.
>
> Go back to those six booleans from the start. This is what replaces them. The
> bad combinations aren't guarded against — **they don't exist.**

---

## Scene 6 — Parallel States

**[04:30 – 05:20]**

### VISUAL

> **DIAGRAM 3** — full frame. The two regions (`playback` and `volume`) should
> be visually separated. Highlight the active state in **each** region
> independently as the events fire, so the audience sees two highlights moving
> at once.

Terminal. **Real output:**

```
start      : ['player.playback.paused', 'player.volume.unmuted']
PLAY       : ['player.playback.playing', 'player.volume.unmuted']
MUTE       : ['player.playback.playing', 'player.volume.muted']
PAUSE      : ['player.playback.paused', 'player.volume.muted']
```

### VOICEOVER

> One more. A media player. It's playing or paused — *and separately* muted or
> unmuted.
>
> Four combinations. The boolean-flag version is where bugs live: pause a muted
> video, unpause it, and now it's loud.
>
> *(beat for the output)*
>
> Two regions, running at once. I paused it — and it stayed muted. That's not
> code I wrote. It's a consequence of the shape.

---

## Scene 7 — The CLI

**[05:20 – 06:15]**

### VISUAL

No diagram. Terminal, full frame:

```bash
xsm generate-template checkout.json --template pythonic-functional
```

Then the generated file, scrolling slowly. Highlight the derived stub names:

```python
def cart_not_empty(...):
    # TODO: implement guard logic

def charge_card(...):
    # TODO: implement service logic
```

### VOICEOVER

> Here's my favourite part. You have the JSON — where do the Python functions
> go?
>
> One command. The CLI reads your machine and writes the scaffolding.
>
> *(beat for the generated file)*
>
> It found every guard and every service, named them in proper Python style,
> and left you `TODO`s.
>
> You never write wiring. You just fill in the logic you actually care about —
> *"is the cart empty," "charge this card."* That's the whole job.
>
> And in this release, every generated file is verified: the library compiles
> its own output and checks it matches your diagram before handing it to you.

---

## Scene 8 — Close

**[06:15 – 07:00]**

### VISUAL

> **DIAGRAM 1, DIAGRAM 2, DIAGRAM 3** side by side, scaled to fit, held for the
> first half of the voiceover.

Then dissolve to the install command on a clean background, large:

```bash
pip install xstate-statemachine
```

End card: repo URL + docs link.

### VOICEOVER

> So — what actually changed here?
>
> You didn't write a scheduler. You didn't write a state variable. You didn't
> write defensive `if`s for combinations that shouldn't happen. You described
> the shape of the problem, and wrote only the logic that was genuinely yours.
>
> That's the pitch. **Think about your logic. Let the structure be structure.**
>
> If you're early in your career, this is one of the highest-leverage ideas you
> can pick up — it comes from statecharts, a design from 1987 that quietly runs
> aircraft and medical devices.
>
> It's one pip install. Bring a diagram you already have in your head.
>
> Docs and examples in the description. Go build something that can't break.

---

## Diagram Cue Sheet

Condensed for the editor — every diagram cut, in order.

| # | Time | Cue | Duration |
|---|---|---|---|
| 1 | 00:35 | **Diagram 2 (2a)** in, arrows animate | ~40s |
| 2 | 01:15 | **Diagram 1**, right half of split, states cycling | ~65s |
| 3 | 02:20 | **Diagram 2 (2b)**, guard highlighted | ~25s |
| 4 | 03:40 | **Diagram 2 (2c)**, failure + RETRY greyed | ~35s |
| 5 | 04:30 | **Diagram 3**, both regions highlighted | ~50s |
| 6 | 06:15 | **Diagrams 1 + 2 + 3** side by side | ~20s |

---

## Accuracy Notes

Keep these exact — they are the claims most likely to be challenged.

- **"a design from 1987"** refers to David Harel's original *statecharts* paper,
  not to this library. The wording deliberately says "it comes from statecharts"
  so it stays accurate. Do not tighten this into "this library has run aircraft
  since 1987."
- **"runs aircraft and medical devices"** describes statecharts as a formalism
  (they are used in avionics and medical device design), not this specific
  Python package. Keep the sentence attached to "statecharts," not to
  `xstate-statemachine`.
- **"every generated file is verified"** is accurate as of `0.7.0`: the CLI
  compiles its emitted code and structurally compares the resulting machine
  against the source JSON before writing. Do not soften or overstate this.
- The **XState JSON uses `guard`** (v5 syntax). If your visualiser is on v4,
  rename `guard:` → `cond:` for rendering only — do not change the JSON shown
  on screen, since the library uses v5 naming.

---

## Distribution Notes

Two suggestions on the plan itself, offered as opinion rather than instruction:

1. **Seven minutes is long for top-of-funnel.** Consider cutting a 60–90 second
   version from Scene 1 + Scene 5 (the hook and impossible states) for social,
   and positioning this full version as the walkthrough people click through to.
   The hook and the `RETRY`-is-ignored moment are the two strongest beats and
   they stand alone.

2. **For the README embed, use a static thumbnail linking to the video.**
   GitHub does not autoplay embedded video, and a large text block above the
   fold tends to bury it. A single diagram image — Diagram 2 is the best
   candidate — with a play overlay linking out will convert better than an
   inline player.
