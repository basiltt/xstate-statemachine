---
title: "xstate-statemachine vs AWS Step Functions"
description: "ASL next to XState JSON for the same order workflow; event-driven transitions, timers, retries, the local-testing story, and when Step Functions is still the right call."
permalink: /guide/vs-step-functions/
---

# xstate-statemachine vs AWS Step Functions

AWS Step Functions is a managed workflow service. You describe a state machine in the Amazon States Language (ASL), and AWS runs it, persists it, retries it and draws it. xstate-statemachine is a library. You describe a statechart in XState JSON and run it in your own Python process, with state in your own store. They overlap on "a JSON state machine that survives failures", and they differ on almost everything else.

{% assign c = site.data.comparisons.workflow_competitors.step_functions %}
This table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json) (`workflow_rows`). Corrections are welcome as PRs against that file. Every row carries a source note. It was checked against the {{ c.checked }}; see the [{{ c.name }} documentation]({{ c.url }}) for the current state.

## Feature table

| Capability | xstate-statemachine | AWS Step Functions | Source |
|:--|:--|:--|:--|
{% for row in site.data.comparisons.workflow_rows %}| {{ row.feature }} | {{ row.ours }} | {{ row.step_functions }} | {{ row.source.step_functions }} |
{% endfor %}

<!-- rows (kept in sync by tests/test_comparisons.py): Definition language; Where it runs; Event-driven transitions; Hierarchy and parallel; Timers; Retries and error handling; Long-running durability; Local testing; Visual editor; Observability; Cost model; Lock-in -->

## The same workflow, side by side

An order: charge the card with retries, wait for the warehouse to confirm shipment, and cancel if nothing arrives within 3 days.

**Step Functions (ASL).** The warehouse wait is a callback task. The workflow hands out a task token and parks until something calls `SendTaskSuccess`:

```json
{
  "StartAt": "Charge",
  "States": {
    "Charge": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": { "FunctionName": "charge-card", "Payload.$": "$" },
      "Retry": [{ "ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 2,
                  "MaxAttempts": 3, "BackoffRate": 2.0, "JitterStrategy": "FULL" }],
      "Catch": [{ "ErrorEquals": ["States.ALL"], "Next": "PaymentFailed" }],
      "Next": "AwaitShipment"
    },
    "AwaitShipment": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sqs:sendMessage.waitForTaskToken",
      "Parameters": { "QueueUrl": "https://sqs.../warehouse",
                      "MessageBody": { "order.$": "$.id", "token.$": "$$.Task.Token" } },
      "TimeoutSeconds": 259200,
      "Catch": [{ "ErrorEquals": ["States.Timeout"], "Next": "Cancelled" }],
      "Next": "Shipped"
    },
    "Shipped": { "Type": "Succeed" },
    "Cancelled": { "Type": "Fail", "Error": "NotShipped" },
    "PaymentFailed": { "Type": "Fail", "Error": "PaymentFailed" }
  }
}
```

**xstate-statemachine (XState JSON).** The wait is a state that listens for an event, with an `after` deadline. The customer can also cancel while it waits, which in ASL would need a second callback path:

```json
{
  "id": "order",
  "initial": "charging",
  "context": { "attempt": 0 },
  "states": {
    "charging": {
      "invoke": { "src": "chargeCard",
                  "onDone": "awaitingShipment",
                  "onError": { "target": "retrying", "actions": "retryBump" } }
    },
    "retrying": {
      "after": { "retryDelay": [ { "target": "charging", "guard": "retryCanRetry" },
                                 { "target": "paymentFailed" } ] }
    },
    "awaitingShipment": {
      "on": { "SHIPPED": "shipped", "CUSTOMER_CANCELLED": "cancelled" },
      "after": { "259200000": "cancelled" }
    },
    "shipped": { "type": "final" },
    "cancelled": { "type": "final" },
    "paymentFailed": { "type": "final" }
  }
}
```

The shapes map closely. `Retry` becomes `RetryPolicy` plus a `retrying` state. `Catch` becomes `onError`, and a `.waitForTaskToken` task becomes a state with `on` events. The difference is in who may move the machine. In ASL, the flow moves from task to task, and outside input enters only through the token you handed out. In a statechart, **any state can react to any event**, so "cancel while waiting", "the address changed while charging" and "pause" are transitions, not extra plumbing.

## Local testing

With Step Functions you test ASL through the `TestState` API, which runs one state at a time against AWS with mocked integrations, and stand up or mock the Lambdas and queues it calls. Step Functions Local, the downloadable emulator, is now marked unsupported by AWS and lacks feature parity. The feedback loop runs through AWS.

Here the chart is tested with pytest in-process. A `SimulatedClock` makes the 3-day timeout instantaneous:

```python
from xstate_statemachine import MachineLogic, SimulatedClock, SyncInterpreter, create_machine
from xstate_statemachine.patterns import RetryPolicy

chart = {"id": "order", "initial": "charging", "context": {"attempt": 0}, "states": {
    "charging": {"invoke": {"src": "chargeCard", "onDone": "awaitingShipment",
                            "onError": {"target": "retrying", "actions": "retryBump"}}},
    "retrying": {"after": {"retryDelay": [{"target": "charging", "guard": "retryCanRetry"},
                                          {"target": "paymentFailed"}]}},
    "awaitingShipment": {"on": {"SHIPPED": "shipped", "CUSTOMER_CANCELLED": "cancelled"},
                         "after": {"259200000": "cancelled"}},
    "shipped": {"type": "final"}, "cancelled": {"type": "final"}, "paymentFailed": {"type": "final"}}}

outcomes = iter([ConnectionError("card network"), "ch_123"])    # fail once, then succeed
def charge_card(i, ctx, e):
    r = next(outcomes)
    if isinstance(r, Exception):
        raise r
    return r

policy = RetryPolicy(max_attempts=3, base_ms=2000, jitter="none")
machine = create_machine(chart, logic=MachineLogic(services={"chargeCard": charge_card}).merge(policy.logic()))

clock = SimulatedClock()
order = SyncInterpreter(machine, clock=clock).start()
assert order.value == "retrying"
clock.increment(2_000)                        # backoff
assert order.value == "awaitingShipment"
clock.increment(3 * 24 * 3_600_000)           # three days, instantly
assert order.value == "cancelled"
```

The same file runs in CI with no Docker, no AWS credentials and no network. `xsm simulate chart.json --events +259200000` does the same from a shell.

## When Step Functions is still the right call

- **You are already all-in on AWS** and the steps are AWS services. Step Functions has direct integrations with 200+ of them (Lambda, ECS, Glue, SageMaker, DynamoDB, SQS), so there is no glue code to write.
- **You want nobody to operate the runtime.** No process to keep alive, no scheduler role, no store to back up. AWS keeps executions for up to a year and retries at the service level.
- **Massive fan-out.** A distributed `Map` state over millions of S3 objects is a single ASL state. Doing that yourself means building a job system.
- **Audit and ops out of the box.** Execution history, CloudWatch metrics, X-Ray traces and console replay come built in. Compliance teams already know how to read them.

## When to choose xstate-statemachine

- The machine is **event-driven**, not a pipeline. Users, webhooks and timers all move it, and any state may need to react to them (a subscription, an order, a chat, a device).
- You want the state machine **inside your application**, running beside your domain code and your database transaction, testable with pytest in milliseconds.
- **Portability.** The same chart runs in XState in the browser and in Python on the server, on any cloud or none.
- **Cost at high event volume.** A library costs your compute only, whereas Step Functions Standard bills per state transition.
- You need **hierarchy and parallel regions** with statechart semantics, and `after` timers that are cancelled automatically when a state exits.

You can also use both. A statechart can own the entity's lifecycle while Step Functions runs a heavy batch job it invokes. The service call is an `invoke`, and the callback arrives as an event.

Related: [Recipes](../recipes/), [APScheduler durable timers](../apscheduler-timers/), [Circuit breaker & retry](../circuit-breaker-retry/), [vs LangGraph](../vs-langgraph/).

New to the library? Start with the [integrations journey](../integrations/): pick your path, then a fifteen-minute tutorial.
