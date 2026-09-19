# Video Diagrams — Statechart Source

Source JSON for the three diagrams referenced in `VIDEO_SCRIPT.md`.

**How to render:** paste each block into the [Stately Visualizer](https://stately.ai/viz)
(or [Stately Editor](https://stately.ai/editor)) and export as SVG or PNG.

**XState version:** these use **v5** syntax (`guard`). If your visualiser is on
v4, rename `guard:` → `cond:` for rendering only. The library itself uses v5
naming, so leave the JSON as-is anywhere it appears on screen.

**Verification:** all three configs were loaded and executed against the
published PyPI package `xstate-statemachine==0.7.0` in a clean virtualenv. The
outputs quoted in the script are real.

---

## Diagram 1 — Traffic Light

**Shows:** three states, `after` timers, a self-returning cycle.
**Used in:** Scene 3 `[01:15]`, Scene 8 `[06:15]`.

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

**Rendering notes**
- The `after` labels (`3000`, `1000`, `4000`) must stay legible — they are the
  point of the scene. If the visualiser renders them small, bump the label size.
- Colour the states green / amber / red. It reads instantly and needs no
  explanation from the voiceover.
- Needs an **animated** variant with the active state highlighted, cycling
  green → yellow → red.

**Verified behaviour**

```
t=0.0s : ['trafficLight.green']
t=3.2s : ['trafficLight.yellow']
t=4.2s : ['trafficLight.red']
```

---

## Diagram 2 — Checkout  ⭐ hero image

**Shows:** guards on transitions, `invoke` with `onDone` / `onError`, a final
state.
**Used in:** Scene 2 `[00:35]`, Scene 4 `[02:20]`, Scene 5 `[03:40]`,
Scene 8 `[06:15]`.

This is the most-used diagram in the video and carries the core argument.
Render it at the highest quality available.

```json
{
  "id": "checkout",
  "initial": "cart",
  "context": { "items": 0, "attempts": 0 },
  "states": {
    "cart": {
      "on": { "CHECKOUT": { "target": "payment", "guard": "cartNotEmpty" } }
    },
    "payment": {
      "invoke": { "src": "chargeCard", "onDone": "success", "onError": "failure" }
    },
    "failure": {
      "on": {
        "RETRY":  { "target": "payment", "guard": "canRetry" },
        "CANCEL": "cart"
      }
    },
    "success": { "type": "final" }
  }
}
```

### Required variants

| Variant | Description | Scene |
|---|---|---|
| **2a** | Plain. All states neutral. | Scene 2 `[00:35]` |
| **2b** | `cartNotEmpty` guard label highlighted on the `cart → payment` arrow. | Scene 4 `[02:20]` |
| **2c** | `failure` highlighted; `RETRY` arrow flashed red then greyed out. | Scene 5 `[03:40]` |

**Rendering notes**
- The guard labels `cartNotEmpty` and `canRetry` **must be readable.** Scene 4
  is built entirely around pointing at one of them.
- `success` is a final state — make sure the double-border marker renders, and
  do not crop it.
- Keep `payment` visually distinct as the async/invoke state; the `onDone` and
  `onError` arrows leaving it should be clearly separable.

**Verified behaviour**

```
empty cart, send CHECKOUT : ['checkout.cart']      <- guard blocked
2 items,   send CHECKOUT : ['checkout.success']    <- guard allowed

payment failed -> ['checkout.failure']
after CANCEL   -> ['checkout.cart']
RETRY from cart-> ['checkout.cart']  <- ignored, not a crash
```

---

## Diagram 3 — Media Player

**Shows:** two parallel regions running independently.
**Used in:** Scene 6 `[04:30]`, Scene 8 `[06:15]`.

```json
{
  "id": "player",
  "type": "parallel",
  "states": {
    "playback": {
      "initial": "paused",
      "states": {
        "paused":  { "on": { "PLAY": "playing" } },
        "playing": { "on": { "PAUSE": "paused" } }
      }
    },
    "volume": {
      "initial": "unmuted",
      "states": {
        "unmuted": { "on": { "MUTE": "muted" } },
        "muted":   { "on": { "UNMUTE": "unmuted" } }
      }
    }
  }
}
```

**Rendering notes**
- The **dashed divider** between `playback` and `volume` is the whole point —
  it is what makes "two things at once" visible. Verify it renders clearly and
  do not crop it out.
- Needs an animated variant where **both** regions show a highlighted active
  state simultaneously. A single moving highlight would undercut the message.
- Side-by-side (horizontal) layout reads better than stacked for this one.

**Verified behaviour**

```
start      : ['player.playback.paused', 'player.volume.unmuted']
PLAY       : ['player.playback.playing', 'player.volume.unmuted']
MUTE       : ['player.playback.playing', 'player.volume.muted']
PAUSE      : ['player.playback.paused', 'player.volume.muted']
```

Note the fourth line: playback returned to `paused` while volume stayed
`muted`. That independence is the takeaway.

---

## Export Checklist

- [ ] Export at **2× or higher** resolution — text must survive video compression
- [ ] Transparent background, or a background matching the video theme
- [ ] All guard labels legible at final playback size
- [ ] Diagram 2 exported in all three variants (2a, 2b, 2c)
- [ ] Diagram 3 divider between regions clearly visible
- [ ] Diagram 1 and Diagram 3 have animated (state-highlighting) versions
- [ ] Diagram 2 also exported as a **static thumbnail** for the README embed
