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
WIZARD_STORE=sqlalchemy flask --app app run             # SQLAlchemyStore over wizard.db (needs [sqlalchemy])
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
step is intact afterwards. `WIZARD_STORE=sqlite` switches to `SQLiteStore`
and `WIZARD_STORE=sqlalchemy` to `SQLAlchemyStore` (a SQLite file here; change
the URL in `make_store` for Postgres or MySQL). Both have no such limit and
cannot be replayed by the client, and both run with `PessimisticLock()`. Use a
server-side store for anything that matters: a signed cookie can be read by
its owner and an older copy can be re-sent.

**Double-clicks and the Back button.** Every form carries a hidden
`step` field naming the step it was rendered for. A double-click, or the
browser's Back button followed by a re-submit, posts a form for a step the
wizard has already left; applied blindly, its empty answers would push the
wizard one step further (`NEXT` is legal from most steps). The view compares
`step` with the machine's state **inside** `act()` and, if they differ, calls
`g.xsm.skip_save()`: nothing is saved and the browser is redirected to the
current step with a flash message. With a server-side store the app also
uses `PessimisticLock()`, so two simultaneous clicks are serialised rather
than one losing with a conflict; on the cookie store a lost race is caught
as `ConflictError` and answered the same way, never a 500.

**CSRF.** When Flask-WTF is installed, `CSRFProtect` is enabled and every
form carries `csrf_token`. Without it the app still runs (a soft
dependency). `test_post_without_token_is_rejected` covers both halves.

**`flask xsm`.** `flask --app app xsm inspect wizard` prints the same report
as `xsm inspect machine.json`, because the registration passes
`source=machine.json`. `diagram`, `docs` and `simulate` work the same way.

## Not in this example

- **Authentication.** The key is a random id in the session, so anyone
  holding the cookie owns the wizard; `authorize=allow_all` is deliberate.
  Real apps key by user and pass a real `authorize=`.
- **The JSON blueprint, idempotency keys and SSE.** See the guide; the
  wizard is HTML forms only.
- **Replay protection on the cookie store.** A client can re-send an older
  signed cookie and rewind its own wizard. Use a server-side store when that
  matters.
- **A production server and a real secret.** `flask run` is the dev server;
  set `WIZARD_SECRET_KEY`.

See the [Flask integration guide](https://basiltt.github.io/xstate-statemachine/guide/integration-flask/).
