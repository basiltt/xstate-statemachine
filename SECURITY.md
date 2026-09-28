# Security Policy

## Supported versions

Security fixes land on the latest minor release only. The library has **zero runtime dependencies**; every integration is an optional extra under `xstate_statemachine.contrib` that you install explicitly.

| Version | Supported |
|:--|:--|
| 0.11.x (current) | ✅ |
| 0.10.x | fixes for critical issues only, until 0.12.0 |
| < 0.10 | ❌ |

## Reporting a vulnerability

Please **do not** open a public issue. Use GitHub's private vulnerability reporting on this repository ("Security" → "Report a vulnerability"), or email the maintainer listed in `pyproject.toml`. Include a minimal reproduction and the affected version. You will get an acknowledgement within 72 hours and a fix or a mitigation plan within 14 days for confirmed issues; we credit reporters in the changelog unless asked not to.

## Trust model

Read this before deploying anything that persists state or accepts events from outside your process.

### Installed packages are fully trusted

`xstate_statemachine` executes the **actions, guards and services you register** — they are your code, with your process's privileges. Extras under `contrib/` import third-party libraries you chose to install. There is no sandbox: a malicious package in your environment can do anything your process can. Nothing in this library discovers or loads plugins implicitly; `contrib` subpackages are imported only when you import them, and the core import path is verified in CI to touch no third-party module.

### The machine definition is trusted; events and snapshots are not

- **Machine JSON** is configuration you author. It is validated for shape (`create_machine`, `xsm validate`, and the `[pydantic]` extra's `validate_machine_json`), never executed. Unknown keys are refused under `strictConfig`.
- **Events** arrive from the outside world. Payloads are opaque to the engine; declare `event_schemas=` (or use the `[pydantic]` extra) to validate them at the `send()` boundary, and `strict=True` to refuse undeclared event types.
- **Snapshots** come back from a store, i.e. from outside the process. They are JSON only (never pickle), size-capped before parsing (`max_snapshot_bytes`, 1 MiB), shape-validated (`SnapshotCorruptError`), checked against the machine's structural hash and version label (`SnapshotDriftError`), and every state id must exist in the machine. A blob you cannot vouch for should be restored with `expected_machine_hash=` so it cannot select its own level of checking.

### What the persistence layer does and does not protect

| Concern | What you get | What you must do |
|:--|:--|:--|
| Concurrent writers | Optimistic locking (`ConflictError`) or a fenced pessimistic lock — never a silent lost update | Choose a `LockStrategy`; keep side effects out of actions or make them idempotent |
| Duplicate deliveries | The idempotency inbox dedupes by `(principal, machine, instance)` + fingerprint | **Pass `principal=`** — it is required, so one tenant can never replay another's outcome |
| Crash between steps | Documented order and the `processed_ids` ring (see the Guarantees page) | Pair timers and retries with the inbox; external side effects go through an outbox |
| Secrets in context | `redact()` denylist applied by every built-in sink (logs, audit log, dead letters) | Extend `redact_keys=`; use a `SnapshotCodec` for encryption at rest; do not put secrets in context |
| Data at rest | `FileStore` directory `0700` / files `0600`; SQLite DB and `-wal`/`-shm` `0600`; `forget(key)` erases every table for an instance | Secure the host; back up; choose retention (`purge_older_than`) |
| Untrusted keys | Store keys are validated (length, NUL, path separators) and `FileStore` percent-encodes them; Redis requires a `prefix` and escapes `SCAN` patterns | Do not derive keys from untrusted input without your own allow-list |

### Redis

The store trusts the connection you hand it. Use `requirepass`/ACLs and TLS (`rediss://`), one `prefix` per application, and Redis persistence (AOF/RDB) if a restart must not lose state. A lock can expire under a slow holder — that is why `persisted()` also fences with the record version.

## Programme-wide baseline

Every integration in this repository is built against a numbered security and operability baseline, tracked in issue [#303](https://github.com/basiltt/xstate-statemachine/issues/303). The [Security](https://basiltt.github.io/xstate-statemachine/guide/security/) and [Guarantees](https://basiltt.github.io/xstate-statemachine/guide/guarantees/) guide pages map each item to the test or CI check that enforces it; every integration page carries a **Guarantees** and a **Threat model** box, and `tests/test_docs_site.py` refuses a page without them.

CI enforces: no `pickle` / `yaml.load` / `eval` / `exec` under `src/` (grep), `pytest-socket` (no accidental network in tests), a zero-dependency import guard for the core, SHA-pinned GitHub Actions, and `pip-audit --strict` over every shipped extra.
