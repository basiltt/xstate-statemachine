# Improvement: deliver service failures as a dedicated `ErrorEvent`, not a `DoneEvent` carrying an exception in `data`

## Summary
`error.platform.*` events are still delivered as a `DoneEvent` whose `data` carries the exception instance. A consumer cannot distinguish "the service completed with output" from "the service failed" by type — it must inspect `event.type` for the `error.` prefix. This was grouped under #60 (LC-52 in the original register) and did not ship in 0.8.0.

## Environment
xstate-statemachine 0.8.0 (commit `9bf6065`), Python 3.13.7, Windows 11, editable install.

## Reproduction
```python
import asyncio
from xstate_statemachine import create_machine, Interpreter, MachineLogic

async def boom(interp, ctx, event):
    raise RuntimeError("venue rejected")

m = create_machine(
    {"id": "m", "initial": "a",
     "states": {"a": {"invoke": {"src": "boom", "onError": {"target": "failed"}}},
                "failed": {}}},
    logic=MachineLogic(services={"boom": boom}),
)
seen = []
class P:
    def on_event_received(self, interp, event): seen.append(event)
i = Interpreter(m).use(P())
async def main():
    await i.start(); await asyncio.sleep(0.05); await i.stop()
    ev = [e for e in seen if str(getattr(e, "type", "")).startswith("error.")][0]
    print("OBSERVED type name :", type(ev).__name__)
    print("OBSERVED .type     :", ev.type)
    print("EXPECTED           : a dedicated ErrorEvent (or `error` attribute), not DoneEvent")
    raise SystemExit(1 if type(ev).__name__ == "DoneEvent" else 0)
asyncio.run(main())
```

## Expected behaviour
XState v5 delivers `error.actor.<id>` / `xstate.error.actor` as a distinct event shape carrying `error`, separate from `xstate.done.actor` which carries `output` (https://stately.ai/docs/invoke#onerror). A typed `ErrorEvent(type, error)` — or at minimum an `error` attribute on the delivered event — lets consumers branch on type rather than string-prefix.

## Proposed fix
Introduce `ErrorEvent` (subclass of `Event`, `error: BaseException`) and emit it for `error.platform.*`; keep `DoneEvent` for `done.invoke.*` / `done.state.*` only. Backwards-compat: `ErrorEvent.data` can alias `.error` for one minor version with a `DeprecationWarning`.

## Acceptance criteria
- [ ] `error.platform.*` events are instances of a dedicated error event class exposing `.error`
- [ ] `DoneEvent` is never used for failure delivery
- [ ] Test: `tests/test_events.py::test_service_failure_delivers_error_event`
- [ ] The script above exits 0

## Related
Split out of #60 (LC-52 in the original register); #33 (error-observability hooks).

