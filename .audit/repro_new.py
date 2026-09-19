"""Reproduce issues #75-#80 against the current checkout."""
import asyncio
import threading
import time
import warnings

from xstate_statemachine import (
    Event,
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)

results = {}


# ---------- #75 receipt keyed on id() ----------
async def r75():
    cfg = {"id": "rc", "initial": "a", "states": {"a": {"on": {"T": "b"}}, "b": {"on": {"T": "a"}}}}
    i = Interpreter(create_machine(cfg))
    await i.start()
    ev = Event(type="T", payload={})
    try:
        await asyncio.wait_for(asyncio.gather(i.send(ev, wait=True), i.send(ev, wait=True)), 2)
        results["75"] = "OK both resolved"
    except asyncio.TimeoutError:
        results["75"] = "DEFECT: hung"
    await i.stop()


# ---------- #76 sync timer inside running loop ----------
async def r76():
    cfg = {"id": "sy", "initial": "a", "states": {"a": {"after": {40: "b"}}, "b": {}}}
    i = SyncInterpreter(create_machine(cfg))
    i.start()
    pend = getattr(i.clock, "pending", "n/a")
    time.sleep(0.12)
    i.tick()
    st = sorted(i.current_state_ids)
    results["76"] = f"{'OK' if st == ['sy.b'] else 'DEFECT'} pending={pend} state={st}"
    i.stop()


def r76_offloop():
    cfg = {"id": "sy", "initial": "a", "states": {"a": {"after": {40: "b"}}, "b": {}}}
    i = SyncInterpreter(create_machine(cfg))
    i.start()
    time.sleep(0.12)
    i.tick()
    results["76-control"] = sorted(i.current_state_ids)
    i.stop()


# ---------- #77 sync macrostep budget ----------
def r77():
    cfg = {"id": "bud", "initial": "a", "context": {"seen": 0},
           "states": {"a": {"on": {"T": {"target": "a", "actions": ["bump"], "reenter": True}}}}}

    def bump(interp, ctx, event, action):
        ctx["seen"] = ctx.get("seen", 0) + 1

    i = SyncInterpreter(create_machine(cfg, logic=MachineLogic(actions={"bump": bump})))
    i.start()
    try:
        i.send_events(["T"] * 1501)
        results["77"] = f"{'OK' if i.context['seen'] == 1501 else 'DEFECT'} seen={i.context['seen']} depth={i.queue_depth}"
    except Exception as e:  # noqa
        results["77"] = f"RAISED {type(e).__name__}: {e} seen={i.context['seen']}"
    i.stop()


# ---------- #78 send_threadsafe bypasses strict ----------
async def r78():
    cfg = {"id": "st", "initial": "a", "strict": True, "states": {"a": {"on": {"FILL": "b"}}, "b": {}}}

    class QtySchema:
        def validate(self, payload):
            qty = (payload or {}).get("qty")
            if not isinstance(qty, int) or qty <= 0:
                raise ValueError("qty must be positive")

    i = Interpreter(create_machine(cfg, event_schemas={"FILL": QtySchema()}), strict=True)
    await i.start()
    out = {}

    def worker(name, *a, **kw):
        try:
            f = i.send_threadsafe(*a, **kw)
            try:
                f.result(1)
                out[name] = "accepted"
            except Exception as e:  # noqa
                out[name] = f"future raised {type(e).__name__}"
        except Exception as e:  # noqa
            out[name] = f"raised {type(e).__name__}"

    for name, args, kw in [("typo", ("FIL",), {}), ("bad", ("FILL",), {"qty": -1})]:
        t = threading.Thread(target=worker, args=(name, *args), kwargs=kw)
        t.start()
        for _ in range(20):
            await asyncio.sleep(0.01)
        t.join(1)
    await asyncio.sleep(0.05)
    results["78"] = f"{out} final={sorted(i.current_state_ids)}"
    await i.stop()


# ---------- #79 reserved-prefix user events ----------
async def r79():
    cfg = {"id": "wc", "initial": "a", "context": {"caught": []}, "states": {"a": {"on": {"*": {"actions": ["note"]}}}}}

    def note(interp, ctx, event, action):
        ctx["caught"].append(event.type)

    i = Interpreter(create_machine(cfg, logic=MachineLogic(actions={"note": note})))
    await i.start()
    for ev in ("PLAIN", "error.myapp.validation", "done.review", "my.namespaced"):
        await i.send(ev)
    await asyncio.sleep(0.05)
    results["79-wildcard"] = i.context["caught"]
    await i.stop()

    cfg2 = {"id": "uh", "initial": "a", "onUnhandled": "error", "states": {"a": {"on": {"X": "a"}}}}
    for ev in ("UNKNOWN_PLAIN", "done.review", "error.validation"):
        j = Interpreter(create_machine(cfg2))
        await j.start()
        try:
            await j.send(ev)
            await asyncio.sleep(0.05)
            results[f"79-onUnhandled[{ev}]"] = f"status={j.status}"
        except Exception as e:  # noqa
            results[f"79-onUnhandled[{ev}]"] = f"raised {type(e).__name__}"
        if j.status == "running":
            await j.stop()


# ---------- #80 error event type ----------
async def r80():
    async def boom(interp, ctx, event):
        raise RuntimeError("venue rejected")

    m = create_machine({"id": "m", "initial": "a",
                        "states": {"a": {"invoke": {"src": "boom", "onError": {"target": "failed"}}}, "failed": {}}},
                       logic=MachineLogic(services={"boom": boom}))
    seen = []

    class P:
        def on_event_received(self, interp, event):
            seen.append(event)

    i = Interpreter(m).use(P())
    await i.start()
    await asyncio.sleep(0.05)
    await i.stop()
    ev = [e for e in seen if str(getattr(e, "type", "")).startswith("error.")]
    results["80"] = [(type(e).__name__, e.type, type(getattr(e, 'data', None)).__name__) for e in ev]


async def main():
    warnings.simplefilter("ignore")
    await r75()
    await r76()
    t = threading.Thread(target=r76_offloop); t.start(); t.join()
    await r78()
    await r79()
    await r80()


asyncio.run(main())
r77()
for k in sorted(results):
    print(f"{k:28} {results[k]}")
