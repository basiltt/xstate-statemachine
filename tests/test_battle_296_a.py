# tests/test_battle_296_a.py
"""#296 battle (A): discovery as an attack surface, concurrency, the 3.9
shim, deprecations and the 1.0 promises."""

from __future__ import annotations

import pathlib
import re
import sys
import threading
import time
import warnings
from typing import Any, Dict, Iterator, List

import pytest

from xstate_statemachine import PluginBase, SyncInterpreter, create_machine
from xstate_statemachine import plugin_discovery as pd
from xstate_statemachine import deprecations as dep

from tests.test_battle_296_scenario import _dist

ROOT = pathlib.Path(__file__).resolve().parents[1]

GOOD = """
from xstate_statemachine import PluginBase
class Good(PluginBase):
    pass
"""


@pytest.fixture
def site(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[pathlib.Path]:
    monkeypatch.delenv(pd.DISABLE_ENV, raising=False)
    monkeypatch.syspath_prepend(str(tmp_path))
    before = set(sys.modules)
    yield tmp_path
    for m in set(sys.modules) - before:
        if m.startswith("bt296a_"):
            del sys.modules[m]


def _machine() -> Any:
    return create_machine(
        {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
    )


class _Fake:
    def __init__(self) -> None:
        self.used: List[Any] = []

    def use(self, p: Any) -> "_Fake":
        self.used.append(p)
        return self


# --------------------------------------------------------------------------
# 1. discovery as an attack surface
# --------------------------------------------------------------------------
class TestCallableEntryPoints:
    def test_loaded_callable_is_never_called(self, site: pathlib.Path) -> None:
        """🔥 `_instantiate` used to CALL any zero-arg callable."""
        code = (
            "import os\nCALLS = []\n"
            "def factory():\n    CALLS.append(1)\n    return None\n"
        )
        _dist(
            site,
            "bt296a-evil",
            "1.0",
            "bt296a_evil",
            code,
            {"evil": "bt296a_evil:factory"},
        )
        assert pd.attach_discovered(_Fake(), allow=["evil"]) == []
        assert sys.modules["bt296a_evil"].CALLS == []

    def test_os_system_entry_point_not_executed(
        self, site: pathlib.Path
    ) -> None:
        _dist(site, "bt296a-os", "1.0", "bt296a_os", "", {"sys": "os:getpid"})
        fake = _Fake()
        with pytest.raises(
            TypeError, match="unmarked factories are not called"
        ):
            pd.attach_discovered(fake, allow=["sys"], strict=True)
        assert fake.used == []

    def test_non_plugin_class_not_constructed(
        self, site: pathlib.Path
    ) -> None:
        code = "MADE = []\nclass X:\n    def __init__(self): MADE.append(1)\n"
        _dist(
            site,
            "bt296a-cls",
            "1.0",
            "bt296a_cls",
            code,
            {"cls": "bt296a_cls:X"},
        )
        assert pd.attach_discovered(_Fake(), allow=["cls"]) == []
        assert sys.modules["bt296a_cls"].MADE == []

    def test_instance_and_dotted_attr_and_extras(
        self, site: pathlib.Path
    ) -> None:
        code = GOOD + "class Holder:\n    Inner = Good\nINST = Good()\n"
        _dist(
            site,
            "bt296a-ok",
            "1.0",
            "bt296a_ok",
            code,
            {
                "dotted": "bt296a_ok:Holder.Inner",
                "inst": "bt296a_ok : INST",
                "extra": "bt296a_ok:Good [fancy]",
            },
        )
        fake = _Fake()
        got = pd.attach_discovered(fake, allow=["bt296a-ok"])
        assert len(got) == 3
        assert all(isinstance(p, PluginBase) for p in got)

    def test_marked_factory_is_called(self, site: pathlib.Path) -> None:
        code = GOOD + (
            "from xstate_statemachine.plugin_discovery import "
            "plugin_factory\n"
            "@plugin_factory\ndef make():\n    return Good()\n"
            "@plugin_factory\ndef bad():\n    return 42\n"
        )
        _dist(
            site,
            "bt296a-f",
            "1.0",
            "bt296a_f",
            code,
            {"make": "bt296a_f:make", "bad": "bt296a_f:bad"},
        )
        got = pd.attach_discovered(_Fake(), allow=["bt296a-f"])
        assert len(got) == 1 and isinstance(got[0], PluginBase)


class TestAllowAndKillSwitch:
    @pytest.mark.parametrize(
        "spelling",
        [
            "xsm_thirdparty_plugin",
            "XSM-ThirdParty-Plugin",
            "xsm.thirdparty.plugin",
        ],
    )
    def test_allow_is_pep503_normalised(
        self, site: pathlib.Path, spelling: str
    ) -> None:
        _dist(
            site,
            "xsm-thirdparty-plugin",
            "1.0",
            "bt296a_tp",
            GOOD,
            {"tp": "bt296a_tp:Good"},
        )
        assert [p.name for p in pd.discover(allow=[spelling])] == ["tp"]

    def test_allow_name_matching_benign_and_hostile(
        self, site: pathlib.Path
    ) -> None:
        """Held: `allow=` by ENTRY name matches every distribution that
        uses the name -- pin the distribution name to exclude a squatter
        (documented in SECURITY.md)."""
        _dist(
            site,
            "bt296a-good",
            "1.0",
            "bt296a_g",
            GOOD,
            {"audit": "bt296a_g:Good"},
        )
        _dist(
            site,
            "bt296a-bad",
            "1.0",
            "bt296a_b",
            GOOD,
            {"audit": "bt296a_b:Good"},
        )
        assert len(pd.discover(allow=["audit"])) == 2
        only = pd.discover(allow=["bt296a-good"])
        assert [p.distribution for p in only] == ["bt296a-good"]
        assert "bt296a_b" in sys.modules  # loaded by the first call

    @pytest.mark.parametrize("val", ["1", "TRUE", " 1 ", "yes", "on", "On"])
    def test_disable_spellings(
        self, site: pathlib.Path, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        _dist(
            site, "bt296a-k", "1.0", "bt296a_k", GOOD, {"k": "bt296a_k:Good"}
        )
        monkeypatch.setenv(pd.DISABLE_ENV, val)
        assert pd.discover() == []
        assert "bt296a_k" not in sys.modules

    @pytest.mark.parametrize("val", ["0", "", "false", "no"])
    def test_enable_spellings(
        self, site: pathlib.Path, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        _dist(
            site, "bt296a-k", "1.0", "bt296a_k", GOOD, {"k": "bt296a_k:Good"}
        )
        monkeypatch.setenv(pd.DISABLE_ENV, val)
        assert [p.name for p in pd.discover(allow=["k"])] == ["k"]


class TestHostileHooks:
    def test_plugin_stopping_interpreter_in_hook(
        self, site: pathlib.Path
    ) -> None:
        code = (
            "from xstate_statemachine import PluginBase\n"
            "class Stopper(PluginBase):\n"
            "    def on_transition(self, i, *a):\n        i.stop()\n"
        )
        _dist(
            site,
            "bt296a-s",
            "1.0",
            "bt296a_s",
            code,
            {"s": "bt296a_s:Stopper"},
        )
        i = SyncInterpreter(_machine())
        pd.attach_discovered(i, allow=["s"])
        i.start()
        i.send("GO")
        assert i.status == "stopped"

    def test_held_blocking_start_hook_is_user_code(self) -> None:
        """Held: a hook that blocks forever blocks `start()` -- plugins are
        in-process user code with no timeout (SECURITY.md: full
        privileges). Asserted via the docs, not by hanging the suite."""
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        assert "full privileges" in text and "allow=" in text


class TestConcurrency:
    def test_concurrent_discover_publishes_whole_results(
        self, site: pathlib.Path
    ) -> None:
        """🔥 last_skipped was cleared/appended in place by every call."""
        bad = "raise ImportError('broken')\n"
        for n in range(4):
            _dist(
                site,
                f"bt296a-x{n}",
                "1.0",
                f"bt296a_x{n}",
                bad,
                {f"x{n}": f"bt296a_x{n}:Nope"},
            )
        errs: List[BaseException] = []
        seen: List[int] = []

        def run() -> None:
            try:
                for _ in range(5):
                    pd.discover(allow=[f"x{n}" for n in range(4)])
                    seen.append(len(pd.last_skipped))
            except BaseException as e:  # pragma: no cover
                errs.append(e)

        ts = [threading.Thread(target=run) for _ in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert not errs
        assert set(seen) == {4}

    def test_reentrant_discover(self, site: pathlib.Path) -> None:
        code = (
            "from xstate_statemachine import plugin_discovery as pd\n"
            "INNER = pd.discover(allow=['bt296a-leaf'])\n" + GOOD
        )
        _dist(
            site,
            "bt296a-leaf",
            "1.0",
            "bt296a_leaf",
            GOOD,
            {"leaf": "bt296a_leaf:Good"},
        )
        _dist(
            site,
            "bt296a-re",
            "1.0",
            "bt296a_re",
            code,
            {"re": "bt296a_re:Good"},
        )
        got = pd.discover(allow=["bt296a-re", "bt296a-leaf"])
        assert {p.name for p in got} == {"re", "leaf"}
        assert [p.name for p in sys.modules["bt296a_re"].INNER] == ["leaf"]


# --------------------------------------------------------------------------
# 2. 3.9 shim + metadata
# --------------------------------------------------------------------------
class TestShim:
    def test_dist_index_built_once_per_call(
        self, site: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """🔥 3.9 `_dist_of` scanned all distributions per entry point."""
        for n in range(60):
            _dist(
                site,
                f"bt296a-m{n}",
                "1.0",
                f"bt296a_m{n}",
                GOOD,
                {f"m{n}": f"bt296a_m{n}:Good"},
            )
        real = pd._entry_points

        class EP:  # a 3.9-style EntryPoint: no `.dist`
            def __init__(self, ep: Any) -> None:
                self.name, self.value, self.group = ep.name, ep.value, ep.group
                self.load = ep.load

        monkeypatch.setattr(
            pd, "_entry_points", lambda g: [EP(e) for e in real(g)]
        )
        calls: List[int] = []
        orig = pd._dist_index
        monkeypatch.setattr(
            pd, "_dist_index", lambda: calls.append(1) or orig()
        )
        t0 = time.perf_counter()
        got = pd.discover(allow=[f"m{n}" for n in range(60)])
        assert len(got) == 60 and len(calls) == 1
        assert {p.distribution for p in got} == {
            f"bt296a-m{n}" for n in range(60)
        }
        assert time.perf_counter() - t0 < 30

    def test_identical_triple_first_dist_wins(self) -> None:
        idx = {("g", "n", "v"): ("first", "1")}
        ep = type("E", (), {"group": "g", "name": "n", "value": "v"})()
        assert pd._dist_of(ep, idx) == ("first", "1")
        assert pd._dist_of(
            type("E", (), {"group": "g", "name": "x", "value": "v"})(), idx
        ) == ("", "")

    def test_malformed_entry_points_txt_does_not_crash(
        self, site: pathlib.Path
    ) -> None:
        info = site / "bt296a_mal-1.0.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(
            "Metadata-Version: 2.1\nVersion: 1.0\n", encoding="utf-8"
        )  # no Name
        (info / "entry_points.txt").write_text(
            "[xstate_statemachine.plugins\nthis is = = not ini\n",
            encoding="utf-8",
        )
        try:
            pd.discover()
        except Exception as exc:  # pragma: no cover - documents behaviour
            pytest.fail(f"malformed metadata crashed discover(): {exc!r}")
        pd._dist_index()


# --------------------------------------------------------------------------
# 3. deprecations
# --------------------------------------------------------------------------
@pytest.fixture
def clean_dep() -> Iterator[None]:
    saved = dict(dep._REGISTRY)
    dep.reset_deprecation_warnings()
    yield
    dep._REGISTRY.clear()
    dep._REGISTRY.update(saved)
    dep.reset_deprecation_warnings()


def _kw() -> Dict[str, str]:
    return dict(since="0.11", removal="2.0", alternative="y")


class TestDeprecations:
    def test_stacklevel_deeper_than_stack(self, clean_dep: None) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assert dep.deprecated("bt-deep", stacklevel=10_000, **_kw())
            assert not dep.deprecated("bt-deep", stacklevel=10_000, **_kw())
        assert len(w) == 1

    def test_two_whats_one_line(self, clean_dep: None) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            for _ in range(3):
                dep.deprecated("bt-a", **_kw())
                dep.deprecated("bt-b", **_kw())  # noqa: E702,E501
        assert len(w) == 2

    def test_seen_overflow_clears_and_repeats(
        self, clean_dep: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Held (documented): past _SEEN_MAX sites the set is cleared, so
        an already-warned site may warn once more."""
        monkeypatch.setattr(dep, "_SEEN_MAX", 3)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            for n in range(4):
                dep.deprecated(f"bt-o{n}", **_kw())
            dep.deprecated("bt-o0", **_kw())
        assert len(w) == 5

    def test_register_last_wins_and_sorted(self, clean_dep: None) -> None:
        dep.register("bt-r", since="1", removal="2", alternative="a")
        dep.register("bt-r", since="1", removal="3", alternative="b")
        mine = [d for d in dep.deprecations() if d.what == "bt-r"]
        assert mine[0].removal == "3"
        whats = [d.what for d in dep.deprecations()]
        assert whats == sorted(whats)

    def test_newline_and_huge_what(self, clean_dep: None) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            dep.deprecated("a\nb", **_kw())
            dep.deprecated("x" * 10_000, **_kw())
        assert len(w) == 2

    def test_register_during_iteration_threads(self, clean_dep: None) -> None:
        stop = threading.Event()
        errs: List[BaseException] = []

        def writer() -> None:
            n = 0
            while not stop.is_set():
                dep.register(
                    f"bt-t{n}", since="1", removal="2", alternative="a"
                )
                n += 1

        t = threading.Thread(target=writer)
        t.start()
        try:
            for _ in range(200):
                try:
                    dep.deprecations()
                except BaseException as e:  # pragma: no cover
                    errs.append(e)
        finally:
            stop.set()
            t.join()
        assert not errs

    def test_known_sites_use_the_helper(self) -> None:
        src = ROOT / "src" / "xstate_statemachine"
        events = (src / "events.py").read_text(encoding="utf-8")
        args = (src / "cli" / "args.py").read_text(encoding="utf-8")
        assert events.count("deprecated(") >= 2
        assert "deprecated(" in args and "--style" in args
        assert re.search(
            r"actionErrorPolicy", " ".join(d.what for d in dep.deprecations())
        ) or "register(" in "".join(
            p.read_text(encoding="utf-8") for p in src.rglob("*.py")
        )


# --------------------------------------------------------------------------
# 4-6. observability, compat matrix, 1.0 checklist
# --------------------------------------------------------------------------
def test_instrument_all_discovered_no_duplicates(site: pathlib.Path) -> None:
    obs = pytest.importorskip("xstate_statemachine.contrib.observability")
    _dist(site, "bt296a-o", "1.0", "bt296a_o", GOOD, {"o": "bt296a_o:Good"})
    i = SyncInterpreter(_machine())
    obs.instrument_all(i, discovered=True, allow=["o"])
    n = len(i._plugins)
    assert n >= 1
    # 🔥 (integrator): a second call used to attach a NEW instance of
    #    every discovered plugin -- one class per interpreter now
    obs.instrument_all(i, discovered=True, allow=["o"])
    assert len(i._plugins) == n
    classes = [type(getattr(p, "wrapped", p)).__name__ for p in i._plugins]
    assert classes.count("Good") == 1, classes


def test_ci_compat_and_smoke_cover_promises() -> None:
    wf = ROOT / ".github" / "workflows"
    compat = (wf / "compat.yml").read_text(encoding="utf-8")
    ci = (wf / "ci.yml").read_text(encoding="utf-8")
    assert "matrix.kind" in compat and "--check" in compat
    assert "all_smoke.py" in ci
    smoke = (ROOT / "scripts" / "verify" / "all_smoke.py").read_text(
        encoding="utf-8"
    )
    assert "core import pulled third-party modules" in smoke


def test_version_triple_agrees() -> None:
    import xstate_statemachine as x

    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', py, re.M)
    log = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    top = re.findall(r"^## \[(\d[^\]]*)\]", log, re.M)[0]
    assert m and x.__version__ == m.group(1) == top
