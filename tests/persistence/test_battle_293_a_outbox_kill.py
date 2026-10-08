# tests/persistence/test_battle_293_a_outbox_kill.py
"""#293 battle, adversary A: ``os._exit(9)`` at every point around the
OUTBOX write (modelled on the #261 inbox kill harness) and two relay
PROCESSES draining one SQLite outbox.

🏛️ Invariant under `PessimisticLock` on a shared `SQLiteStore`: the
snapshot and its outbox rows commit together or not at all.
"""

from __future__ import annotations

import faulthandler
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Any, List

from src.xstate_statemachine.eda import Envelope, SQLiteOutboxStore
from src.xstate_statemachine.persistence import SQLiteStore

ROOT = pathlib.Path(__file__).resolve().parents[2]
WATCHDOG_S = 60
CHILD_TIMEOUT_S = 30

CFG = {
    "id": "order",
    "initial": "open",
    "context": {"total": 7},
    "states": {
        "open": {
            "on": {
                "PAY": {
                    "target": "paid",
                    "meta": {"publish": {"type": "order.paid"}},
                }
            }
        },
        "paid": {"tags": ["publish"]},
    },
}

KILL_CHILD = r"""
import json, os, sys
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
from src.xstate_statemachine import create_machine
from src.xstate_statemachine.eda import OutboxPlugin, SQLiteOutboxStore
from src.xstate_statemachine.persistence import (
    PessimisticLock, SQLiteStore, persisted)

store = SQLiteStore(args["db"])
outbox = SQLiteOutboxStore(store)
point = args["point"]
die = lambda: os._exit(9)
real_save, real_add = store.save, outbox.add
def save(*a, **k):
    if point == "before_save":
        die()
    real_save(*a, **k)
    if point == "after_save":
        die()
store.save = save
adds = [0]
def add(*a, **k):
    real_add(*a, **k)
    adds[0] += 1
    if point == "after_first_add" or (point == "after_all_adds"
                                      and adds[0] == 2):
        die()
outbox.add = add
with persisted(store, "o-1", create_machine(args["cfg"]),
               lock=PessimisticLock(timeout=5),
               plugins=[OutboxPlugin(outbox)]) as i:
    i.send("PAY")
if point == "after_exit":
    die()
"""

RELAY_CHILD = r"""
import json, sys
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
from src.xstate_statemachine.eda import OutboxRelay, SQLiteOutboxStore

class Log:
    def publish(self, topic, env):
        with open(args["log"], "a") as f:
            f.write(env.id + "\n")

relay = OutboxRelay(SQLiteOutboxStore(args["db"]), Log(), batch=5)
while relay.relay_once_sync():
    pass
"""


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        faulthandler.dump_traceback_later(WATCHDOG_S, exit=True)
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="b293a_"))

    def tearDown(self) -> None:
        faulthandler.cancel_dump_traceback_later()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def spawn(self, code: str, **args: Any) -> "subprocess.Popen[bytes]":
        args["root"] = str(ROOT)
        return subprocess.Popen(
            [sys.executable, "-c", code, json.dumps(args)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


class TestOutboxKill(_Base):
    """💀 Kill at each point; the snapshot and its rows agree."""

    def _killed_at(self, point: str) -> None:
        db = self.tmp / f"{point}.db"
        p = self.spawn(KILL_CHILD, db=str(db), point=point, cfg=CFG)
        _, err = p.communicate(timeout=CHILD_TIMEOUT_S)
        self.assertEqual(p.returncode, 9, err.decode(errors="replace"))
        store = SQLiteStore(db)
        try:
            outbox = SQLiteOutboxStore(store)
            rows = outbox.count()
            saved = store.load("o-1") is not None
        finally:
            store.close()
        if saved:
            self.assertEqual(rows, 2, point)  # ✅ both envelopes
        else:
            self.assertEqual(rows, 0, point)  # ✅ nothing orphaned
        expect_saved = point == "after_exit"
        self.assertEqual(saved, expect_saved, point)

    def test_every_kill_point(self) -> None:
        for point in (
            "before_save",
            "after_save",
            "after_first_add",
            "after_all_adds",
            "after_exit",
        ):
            with self.subTest(point=point):
                self._killed_at(point)


class TestTwoRelayProcesses(_Base):
    def test_each_row_published_once(self) -> None:
        db = self.tmp / "o.db"
        outbox = SQLiteOutboxStore(str(db))
        ids: List[str] = []
        for n in range(300):
            env = Envelope.new(type="x", data={"n": n})
            ids.append(env.id)
            outbox.add("t", env)
        outbox.close()
        # ⚠️ one log per process: Windows appends are not atomic across
        #    processes, a shared file loses lines.
        logs = [self.tmp / f"log{k}.txt" for k in range(3)]
        procs = [
            self.spawn(RELAY_CHILD, db=str(db), log=str(log)) for log in logs
        ]
        for p in procs:
            _, err = p.communicate(timeout=CHILD_TIMEOUT_S)
            self.assertEqual(p.returncode, 0, err.decode(errors="replace"))
        seen = [
            i for log in logs if log.exists() for i in log.read_text().split()
        ]
        self.assertEqual(sorted(seen), sorted(ids))  # 📝 none twice
        outbox = SQLiteOutboxStore(str(db))
        self.assertEqual(outbox.count(pending_only=True), 0)
        outbox.close()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
