"""LC-53 repro: three production-critical characteristics are undocumented.

Measured in this study but absent from `docs/_guide/`:

1. **Timer starvation** -- `after` deadlines are ordinary coroutines on the
   shared event loop; at 500 busy interpreters a 10 ms timer fires ~2,250 ms
   late (`bench_c_timers.py`).
2. **`SyncInterpreter` threading model** -- `after` timers run on background
   `threading.Thread`s that mutate context with no lock, while `send()` runs
   the macrostep on the calling thread (`bench_f`).
3. **Global throughput budget** -- one asyncio loop, one thread: 18,152 ev/s
   aggregate at N=1,000 interpreters, i.e. 18.2 ev/s each (`bench_b2`).

This scans the guide pages a reader would consult for each topic.
Exits 1 if any topic is undocumented.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

# Locate the shipped guide: env override, else walk up from CWD looking for a
# checkout of the library, else assume we are running inside one.
def _find_guide() -> pathlib.Path:
    env = os.environ.get("XSM_REPO")
    if env:
        return pathlib.Path(env) / "docs" / "_guide"
    here = pathlib.Path.cwd().resolve()
    for base in (here, *here.parents):
        cand = base / "docs" / "_guide"
        if (cand / "interpreters.md").is_file():
            return cand
    return here / "docs" / "_guide"


GUIDE = _find_guide()

TOPICS = {
    "timer starvation / delayed-transition accuracy under load": (
        ["delayed-transitions.md", "interpreters.md", "faq.md"],
        [r"starv", r"timer (drift|accuracy|precision)", r"fires? late", r"under load"],
    ),
    "SyncInterpreter threading model (after timers on unlocked background threads)": (
        ["interpreters.md", "delayed-transitions.md"],
        [r"threading\.timer", r"background thread", r"worker thread", r"thread-safe"],
    ),
    "global throughput budget (one loop, one thread, shared ev/s)": (
        ["interpreters.md", "faq.md", "services.md"],
        [r"ev/s", r"events per second", r"throughput", r"global budget"],
    ),
}


def main() -> int:
    if not GUIDE.is_dir():
        print("OBSERVED  guide directory not found:", GUIDE)
        print("HINT      set XSM_REPO=/path/to/xstate-statemachine")
        return 1
    print(f"OBSERVED  scanning docs/_guide/ ({len(list(GUIDE.glob('*.md')))} pages present)")

    undocumented = []
    for topic, (pages, patterns) in TOPICS.items():
        corpus = "\n".join(
            (GUIDE / p).read_text(encoding="utf-8", errors="replace")
            for p in pages
            if (GUIDE / p).is_file()
        ).lower()
        hits = [p for p in patterns if re.search(p, corpus)]
        print(f"OBSERVED  {topic!r}\n            pages={pages} matched={hits or 'NONE'}")
        if not hits:
            undocumented.append(topic)

    print("OBSERVED  undocumented topics:", undocumented)
    print(
        "EXPECTED  all three production characteristics documented, with the "
        "measured numbers (+2,250 ms timer error @500 machines; SyncInterpreter "
        "threading contract; ~18k ev/s global budget)"
    )
    ok = not undocumented
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
