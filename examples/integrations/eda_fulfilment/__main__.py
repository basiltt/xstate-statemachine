"""``python -m eda_fulfilment [--broker fake|redis-streams]``.

Run from ``examples/integrations`` (or with that folder on PYTHONPATH).
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# 📝 The modules import each other flat (``import logic``), like the other
#    example apps; make that work under ``-m`` too.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eda_fulfilment")
    parser.add_argument("--broker", choices=app.BROKERS, default=None)
    args = parser.parse_args(argv)
    # 📝 The poison message logs a traceback on every attempt by design;
    #    keep the demo output to the summary.
    logging.basicConfig(level=logging.CRITICAL)
    summary = app.run_demo(args.broker or "fake")
    print("eda_fulfilment demo")
    for key, value in summary.items():
        if key == "orders":
            for order, states in value.items():
                print(f"  {order:<22} {', '.join(states or ['-'])}")
        else:
            print(f"  {key:<22} {value}")
    ok = all(s == ["order.shipped"] for s in summary["orders"].values()) and (
        summary["dead_letters"] == 1
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
