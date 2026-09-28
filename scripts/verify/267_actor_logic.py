"""Verification for #267 (A10 actor logic). `python scripts/verify/267_actor_logic.py`.

Runs against the installed package. The issue's async-iterator scenario,
the sync twin, a from_callback pushing 1,000 events from a background
thread (in order, none lost) with receive() via sendTo and cleanup exactly
once, on both engines.
"""

from __future__ import annotations

import asyncio
import threading
import time


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import (
        Interpreter,
        MachineLogic,
        SyncInterpreter,
        create_machine,
        from_async_iterator,
        from_callback,
        from_iterator,
        to_promise,
    )

    step("from_async_iterator: 'hel' + 'lo' -> onDone (issue scenario)")

    async def chunks(i, c, e):  # noqa: ANN001
        for w in ["hel", "lo"]:
            yield w

    cfg = {
        "id": "s",
        "initial": "streaming",
        "context": {"buf": ""},
        "states": {
            "streaming": {
                "invoke": {"src": "stream", "onDone": "done"},
                "on": {"STREAM": {"actions": "append"}},
            },
            "done": {"type": "final"},
        },
    }

    def append(i, c, e, a):  # noqa: ANN001
        c["buf"] = c["buf"] + e.payload["data"]

    async def go() -> str:
        i = await Interpreter(
            create_machine(
                cfg,
                logic=MachineLogic(
                    actions={"append": append},
                    services={"stream": from_async_iterator(chunks)},
                ),
            )
        ).start()
        await to_promise(i)
        return i.context["buf"]

    buf = asyncio.run(go())
    print("  ", buf)
    assert buf == "hello"

    step("from_iterator on the sync engine")

    def sync_chunks(i, c, e):  # noqa: ANN001
        yield from ["hel", "lo"]

    si = SyncInterpreter(
        create_machine(
            cfg,
            logic=MachineLogic(
                actions={"append": append},
                services={"stream": from_iterator(sync_chunks)},
            ),
        )
    ).start()
    for _ in range(200):
        si.tick()
        if si.status == "done":
            break
        time.sleep(0.005)
    print("  ", si.context["buf"], si.status)
    assert si.context["buf"] == "hello" and si.status == "done"

    step(
        "from_callback: 1000 events from a thread, receive(), cleanup once (both engines)"
    )
    cb_cfg = {
        "id": "cb",
        "initial": "on",
        "context": {"seen": []},
        "states": {
            "on": {
                "invoke": {"src": "cb", "id": "conn"},
                "on": {
                    "TICK": {"actions": "rec"},
                    "PING": {
                        "actions": {
                            "type": "sendTo",
                            "params": {
                                "to": "conn",
                                "event": {"type": "HELLO", "n": 7},
                            },
                        }
                    },
                    "OFF": "off",
                },
            },
            "off": {},
        },
    }

    def make_logic(
        cleaned: list, got: list, pushed: threading.Event
    ) -> MachineLogic:
        def setup(send_back, receive, ctx, event):  # noqa: ANN001
            receive(lambda ev: got.append(ev.payload["n"]))

            def push() -> None:
                for k in range(1000):
                    send_back("TICK", k=k)
                pushed.set()

            threading.Thread(target=push).start()
            return lambda: cleaned.append(1)

        return MachineLogic(
            actions={
                "rec": lambda i, c, e, a: c["seen"].append(e.payload["k"])
            },
            services={"cb": from_callback(setup)},
        )

    cleaned, got, pushed = [], [], threading.Event()
    si = SyncInterpreter(
        create_machine(cb_cfg, logic=make_logic(cleaned, got, pushed))
    ).start()
    pushed.wait(5)
    si.tick()
    si.send("PING")
    si.send("OFF")
    si.stop()
    print(
        f"  sync: delivered={len(si.context['seen'])} ordered={si.context['seen'] == list(range(1000))} receive={got} cleanup={cleaned}"
    )
    assert (
        si.context["seen"] == list(range(1000))
        and got == [7]
        and cleaned == [1]
    )

    cleaned, got, pushed = [], [], threading.Event()

    async def go2() -> tuple:
        i = await Interpreter(
            create_machine(cb_cfg, logic=make_logic(cleaned, got, pushed))
        ).start()
        await asyncio.get_running_loop().run_in_executor(None, pushed.wait, 5)
        for _ in range(400):
            await asyncio.sleep(0.005)
            if len(i.context["seen"]) == 1000:
                break
        await i.send("PING", wait=True)
        await i.send("OFF", wait=True)
        seen = list(i.context["seen"])
        await i.stop()
        return seen

    seen = asyncio.run(go2())
    print(
        f"  async: delivered={len(seen)} ordered={seen == list(range(1000))} receive={got} cleanup={cleaned}"
    )
    assert seen == list(range(1000)) and got == [7] and cleaned == [1]

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
