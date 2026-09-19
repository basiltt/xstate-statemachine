"""Verify the reopened-issue residual claims."""
import asyncio, inspect, warnings
from xstate_statemachine import Interpreter, SyncInterpreter, MachineLogic, create_machine
from xstate_statemachine.resolver import resolve_target_state

warnings.simplefilter("always")
out = {}

# #27: raise emitted before failing action survives rollback?
async def r27():
    cfg = {"id": "rs", "initial": "a", "actionErrorPolicy": "rollback", "context": {"seen": []},
           "states": {"a": {"on": {"GO": {"target": "b", "actions": [{"type": "raise", "params": {"event": "PING"}}, "boom"]},
                                  "PING": {"actions": ["note"]}}},
                      "b": {"on": {"PING": {"actions": ["note"]}}}}}
    def boom(i, c, e, a): raise RuntimeError("x")
    def note(i, c, e, a): c["seen"].append(e.type)
    i = Interpreter(create_machine(cfg, logic=MachineLogic(actions={"boom": boom, "note": note})))
    await i.start(); await i.send("GO"); await asyncio.sleep(0.05)
    out["27 raise survives rollback"] = f"state={sorted(i.current_state_ids)} seen={i.context['seen']}"
    await i.stop()

# #31: sibling fallback warns?
def r31():
    m = create_machine({"id": "m", "initial": "A", "states": {"A": {"initial": "A1", "states": {"A1": {}}}, "B": {}}})
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        n = resolve_target_state(".B", m.states["A"])
    out["31 sibling fallback"] = f"resolved={n.id} warnings={[str(x.message)[:60] for x in w]}"

# #43: tasks per idle child
async def r43():
    child = {"id": "c", "initial": "idle", "states": {"idle": {"on": {"X": "done"}}, "done": {"type": "final"}}}
    cm = create_machine(child)
    N = 10
    cfg = {"id": "p", "initial": "run", "states": {"run": {"invoke": [{"id": f"k{n}", "src": "kid"} for n in range(N)]}}}
    i = Interpreter(create_machine(cfg, logic=MachineLogic(services={"kid": cm})))
    before = len(asyncio.all_tasks())
    await i.start(); await asyncio.sleep(0.1)
    after = len(asyncio.all_tasks())
    out["43 tasks/child"] = f"{(after - before - 1) / N:.1f} (delta {after-before} for {N} children + parent loop)"
    await i.stop()

# #44: status after static restore
async def r44():
    async def svc(i, c, e):
        await asyncio.sleep(10)
    cfg = {"id": "r", "initial": "w", "states": {"w": {"invoke": {"src": "svc"}}}}
    m = create_machine(cfg, logic=MachineLogic(services={"svc": svc}))
    i = Interpreter(m); await i.start(); await asyncio.sleep(0.02)
    snap = i.get_snapshot(); await i.stop()
    j = Interpreter.from_snapshot(snap, m); await j.start(); await asyncio.sleep(0.02)
    out["44 restored status"] = f"status={j.status} pending={[p.invoke_id for p in j.pending_invocations()]}"
    await j.stop()

# #52: MachineLogic(strict=?)
def r52():
    sig = inspect.signature(MachineLogic.__init__)
    out["52 MachineLogic params"] = list(sig.parameters)

async def main():
    await r27(); await r43(); await r44()
asyncio.run(main()); r31(); r52()
for k, v in out.items(): print(f"{k:28} {v}")
