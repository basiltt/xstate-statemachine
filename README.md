# XState Machine

A robust, asynchronous, and feature-complete Python library for parsing and executing state machines defined in XState-compatible JSON.

This library provides a powerful interpreter that understands hierarchical, parallel, and asynchronous state machines, including invoked services and delayed transitions.

## Features

-   **XState Compatible**: Parses JSON configurations from XState.
-   **Fully Asynchronous**: Built on `asyncio` for modern, non-blocking applications.
-   **Machine Types**: Supports Standard, Hierarchical, Parallel, and Final states.
-   **Advanced Transitions**: Correctly handles `invoke` for services and `after` for timed events.
-   **Clean Architecture**: Strong separation between machine definition and its implementation.
-   **Developer Friendly**: Full type hinting, comprehensive logging, and clear documentation.

## Installation

```bash
pip install xstate-machine
