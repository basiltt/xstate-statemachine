# Shared XState v5 conformance cases

These 50 JSON files are the executable specification of the statechart
engine that this library shares with its Rust port
(`xstate-statemachine-rs`, `conformance/cases/`). Each case holds a machine,
stubbed logic, a list of steps and the observations the **real** XState engine
made (`expected.xstate`, recorded with `xstate@5.33.3` under Node by
`conformance/tools/xstate_oracle/oracle.mjs`).

`tests/test_xstate_conformance_cases.py` replays every case on the Python
engine and asserts it observes exactly what XState did (`state_ids`,
`context`, `actions`, `status`, `guards`, `output`), so XState parity is a
permanent regression test that runs in CI.

Provenance: copied from `xstate-statemachine-rs` at commit
`cfb081765caf53b883dcf3d2571c5a346c14479e` (2026-11-04). To refresh, copy
the Rust repository's `conformance/cases/*.json` over this directory and
update this commit reference; set `XSM_CONFORMANCE_CASES` to point the test
at another directory without copying.
