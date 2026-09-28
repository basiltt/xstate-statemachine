---
title: "<Framework> integration"
description: "One sentence: what a <Framework> developer gets."
---

<!--
  📐 Template for every `xstate_statemachine.contrib.<name>` page (programme #257).
  Copy to docs/_guide/integration-<name>.md, keep every section, delete this comment.
  `tests/test_docs_site.py` asserts the Guarantees and Threat-model boxes exist.
-->

# <Framework>

One paragraph: the problem a <Framework> developer has today and what this extra makes trivial.

## Install

```bash
pip install "xstate-statemachine[<extra>]"
```

Requires <Framework> `>=X.Y`. Tested versions are in the [compatibility table](#compatibility).

## Quick start

<!-- doc-requires: <module> -->
```python
# 10-20 lines a reader can paste. Executed in CI when the extra is installed.
```

## Reference

Every public name, one subsection each: signature, what it does, what it raises.

## Guarantees

> **What this does:** …
>
> **What this does not do:** …
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** …
>
> **What it exposes:** …
>
> **You must configure:** an `authorize=` callable; …

## Compatibility

| <Framework> | Python | Tested in CI |
|:--|:--|:--|
| X.Y – Z.W | 3.9 – 3.14 | ✅ |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[<extra>]"` | extra not installed | run the command |
