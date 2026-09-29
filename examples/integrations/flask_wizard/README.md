# Flask wizard — a 4-step onboarding flow as a statechart

A server-rendered onboarding wizard built on `xstate-statemachine[flask]`.
Each browser session gets its own machine. **Next** and **Back** are events,
and the chart decides which ones are legal from each step.

```
account ──NEXT (hasAccount)──▶ profile ──NEXT──▶ plan ──NEXT (validPlan)──▶ confirm ──SUBMIT──▶ done
   ▲                              │  ▲             │  ▲                        │
   └────────────BACK──────────────┘  └────BACK─────┘  └──────────BACK──────────┘
```

| File | What it is |
|:--|:--|
| `machine.json` | The chart. Passes `xsm validate --plain`. |
| `app.py` | `create_app()`: the `XState` extension, the session-keyed registration, the store switch, CSRF, and three routes. |
| `templates/` | One Jinja page per step, plus `too_large.html`. |
| `tests/` | Plain pytest with Flask's test client. |

## Run it

```bash
pip install "xstate-statemachine[flask]" flask-wtf     # flask-wtf is optional (CSRF)
cd examples/integrations/flask_wizard
flask --app app run                                     # http://127.0.0.1:5000/
WIZARD_STORE=sqlite flask --app app run                 # server-side store (wizard.db)
flask --app app xsm inspect wizard                      # the chart, from the CLI
python -m pytest tests -q
```

On Windows PowerShell, set the variable with `$env:WIZARD_STORE = "sqlite"`.
Set `WIZARD_SECRET_KEY` to a real secret anywhere but your laptop: it signs
the session cookie that holds the wizard.

## What to look at

**One machine per browser.** The registration passes
`key=lambda: session.setdefault("wizard_id", uuid4().hex)`, so
`g.xsm.act("wizard")` with no key opens *this* browser's wizard. The test
`test_two_clients_advance_independent_wizards` drives two clients to
different steps and checks neither sees the other's answers.

**Navigation is events.** `POST /next`, `/back` and `/submit` send `NEXT`,
`BACK` and `SUBMIT`. There is no `step` integer to get out of sync. Step 1's
`NEXT` is guarded by `hasAccount`, and `SUBMIT` from step 1 is simply not a
transition, so the receipt comes back unchanged and the page shows a
message. Going **Back** keeps what was typed, because the answers live in
the machine's `context`.

**Reads never write.** `GET /` uses `g.xsm.peek(...)`, which renders the
current step without saving. `act()` refuses to run inside a GET (405), so
every change is a POST followed by a redirect.

**Where the state lives.** By default it is `SessionStore`: the snapshot
rides in Flask's **signed** session cookie, with a hard 3 KiB cap. If an
answer would push it over, `SessionStoreTooLargeError` is raised, `act()`
saves nothing, and the app answers 413 with `too_large.html`. The test
`test_oversize_context_is_refused_in_the_cookie` checks that the previous
step is intact afterwards. `WIZARD_STORE=sqlite` switches to `SQLiteStore`,
which has no such limit and cannot be replayed by the client. Use a
server-side store for anything that matters: a signed cookie can be read by
its owner and an older copy can be re-sent.

**CSRF.** When Flask-WTF is installed, `CSRFProtect` is enabled and every
form carries `csrf_token`. Without it the app still runs (a soft
dependency). `test_post_without_token_is_rejected` covers both halves.

**`flask xsm`.** `flask --app app xsm inspect wizard` prints the same report
as `xsm inspect machine.json`, because the registration passes
`source=machine.json`. `diagram`, `docs` and `simulate` work the same way.

See the [Flask integration guide](../../../docs/_guide/integration-flask.md).
