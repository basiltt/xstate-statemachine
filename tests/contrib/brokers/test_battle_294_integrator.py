# tests/contrib/brokers/test_battle_294_integrator.py
"""#294 integrator: the adversaries' cross-area notes, closed.

* `KafkaBroker(sasl_plain_password=...)` died with ``TypeError:
  _Core.__init__()`` -- it now names the option and where client options
  go;
* `xsm asyncapi --protocol bogus` exited 0 -- the protocol is one of the
  AsyncAPI binding names;
* `xsm dlq` on a missing store file said ``xsm snapshots: error:``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from xstate_statemachine.contrib.brokers._base import SyncBroker

ROOT = Path(__file__).resolve().parents[3]


class _T:
    def send(self, topic, env):  # pragma: no cover - never called
        pass

    def fetch(self, topic, wait_s):  # pragma: no cover
        return []

    def ack(self, native):  # pragma: no cover
        pass

    def drop(self, native):  # pragma: no cover
        pass


def test_unknown_adapter_option_is_named_with_a_hint() -> None:
    with pytest.raises(TypeError) as ei:
        SyncBroker(_T(), sasl_plain_password="s3cret", max_bytes=10)
    msg = str(ei.value)
    assert "sasl_plain_password" in msg and "client=" in msg
    assert "s3cret" not in msg  # the VALUE never appears
    # the Kafka adapter names ITS client option (review L2)
    pytest.importorskip("aiokafka")
    from xstate_statemachine.contrib.brokers.kafka import KafkaBroker

    with pytest.raises(TypeError, match="client_kw"):
        KafkaBroker(bootstrap_servers="x:1", sasl_plain_password="s3cret")


def _xsm(*args: str) -> "subprocess.CompletedProcess[str]":
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "--plain", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_asyncapi_protocol_is_a_known_binding(tmp_path: Path) -> None:
    chart = ROOT / "examples" / "integrations" / "eda_fulfilment"
    p = _xsm("asyncapi", str(chart / "machine.json"), "--protocol", "bogus")
    assert p.returncode == 2, p.stdout + p.stderr
    assert "invalid choice" in p.stderr and "kafka" in p.stderr
    p = _xsm("asyncapi", str(chart / "machine.json"), "--protocol", "amqp")
    assert p.returncode == 0, p.stderr[-500:]


def test_dlq_error_lines_name_xsm_dlq(tmp_path: Path) -> None:
    p = _xsm("dlq", "--dlq", f"sqlite:///{tmp_path / 'nope.db'}", "list")
    assert p.returncode == 2
    assert p.stderr.startswith("xsm dlq: error:"), p.stderr
    assert "xsm snapshots" not in p.stderr
    # and `xsm snapshots` still says its own name afterwards
    p = _xsm("snapshots", "list", "--store", f"sqlite:///{tmp_path / 'n.db'}")
    assert "xsm snapshots: error:" in p.stderr or p.returncode == 0, p.stderr
