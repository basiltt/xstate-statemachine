---
title: "CLI Templates Deep Dive"
description: "All 5 code generation templates explained with complete generated output."
---

# CLI Templates Deep Dive

The `xsm` CLI offers five code generation templates, each producing a different code structure and API style. This guide shows the **complete generated output** for each template using the same input JSON, so you can compare them side-by-side and choose the best fit for your project.

## Template Overview

| Template | API Style | JSON at Runtime? | Logic Pattern | Default Mode |
|----------|-----------|:-----------------:|---------------|:------------:|
| `pythonic-class` | `StateMachine` subclass | No | Class methods with decorators | sync |
| `pythonic-builder` | `MachineBuilder` chain | No | Module-level functions with decorators | sync |
| `pythonic-functional` | `build_machine()` call | No | Module-level functions with decorators | sync |
| `class-json` | Class-based provider | Yes | Class methods (camelCase) | async |
| `function-json` | Module functions | Yes | Module-level functions | async |

## Input JSON Example

All examples below use this `checkout.json` as input:

```json
{
  "id": "checkout",
  "initial": "cart",
  "context": { "items": [], "total": 0 },
  "states": {
    "cart": {
      "on": {
        "SUBMIT": {
          "target": "payment",
          "guard": "cartNotEmpty",
          "actions": "calculateTotal"
        }
      }
    },
    "payment": {
      "invoke": {
        "src": "processPayment",
        "onDone": { "target": "confirmed", "actions": "clearCart" },
        "onError": { "target": "cart", "actions": "showError" }
      }
    },
    "confirmed": {
      "type": "final"
    }
  }
}
```

This machine has:
- **3 states**: `cart`, `payment`, `confirmed` (final)
- **1 guard**: `cartNotEmpty`
- **3 actions**: `calculateTotal`, `clearCart`, `showError`
- **1 service**: `processPayment` (via `invoke`)
- **1 event**: `SUBMIT`

---

## Template 1: `pythonic-class`

The `pythonic-class` template generates a `StateMachine` subclass with `State()` attributes, `.to()` transitions, and `@action` / `@guard` / `@service` decorated methods. **No JSON is needed at runtime** — the machine definition is compiled directly into Python.

### Command

```bash
xsm gt checkout.json --template pythonic-class --async-mode no
```

### Generated Logic File: `checkout_logic.py`

```python
from typing import Any, Dict, Union
from xstate_statemachine import (
    StateMachine,
    State,
    Interpreter,
    SyncInterpreter,
    action,
    guard,
    service,
)
import logging

logger = logging.getLogger(__name__)


class CheckoutMachine(StateMachine):
    """Checkout state machine using the declarative class-based API."""

    machine_id = "checkout"
    initial_context = {'items': [], 'total': 0}

    cart = State(initial=True)
    payment = State(invoke={'src': 'processPayment', 'onDone': {'target': 'confirmed', 'actions': 'clearCart'}, 'onError': {'target': 'cart', 'actions': 'showError'}})
    confirmed = State()

    # Transitions
    submit = cart.to(payment, event="SUBMIT", actions="calculateTotal", guard="cartNotEmpty")

    # Actions
    @action
    def calculate_total(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Action handler for ``calculateTotal``.

        Called when the SUBMIT transition fires.
        """
        try:
            logger.info("Executing action: calculateTotal")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Error in action calculateTotal")
            raise

    @action
    def clear_cart(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Action handler for ``clearCart``.

        Called when processPayment completes successfully.
        """
        try:
            logger.info("Executing action: clearCart")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Error in action clearCart")
            raise

    @action
    def show_error(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Any,
        action_def: Any,
    ) -> None:
        """
        Action handler for ``showError``.

        Called when processPayment encounters an error.
        """
        try:
            logger.info("Executing action: showError")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Error in action showError")
            raise

    # Guards
    @guard
    def cart_not_empty(
        self,
        context: Dict[str, Any],
        event: Any,
    ) -> bool:
        """
        Guard for ``cartNotEmpty``.

        Returns True to allow the transition, False to block it.
        """
        logger.info("Evaluating guard: cartNotEmpty")
        # TODO: implement guard logic
        return True

    # Services
    @service
    def process_payment(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Any,
    ) -> Dict[str, Any]:
        """
        Service handler for ``processPayment``.

        Returns a dict that becomes the onDone event data.
        """
        try:
            logger.info("Running service: processPayment")
            # TODO: implement service logic
            return {"result": "done"}
        except Exception:
            logger.exception("Error in service processPayment")
            raise
```

### Generated Runner File: `checkout_runner.py`

```python
import logging
from xstate_statemachine import SyncInterpreter

from checkout_logic import CheckoutMachine

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Executes the simulation for the checkout machine."""

    machine = CheckoutMachine.create_machine()

    # Interpreter Setup
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f'Initial state: {interpreter.current_state_ids}')

    # Event Simulation
    logger.info('Sending event: %s', 'SUBMIT')
    interpreter.send("SUBMIT")

    interpreter.stop()

if __name__ == "__main__":
    main()
```

> **Key Feature:** The runner calls `CheckoutMachine.create_machine()` — no JSON loading needed. The machine definition is compiled from the class attributes at runtime.

---

## Template 2: `pythonic-builder`

The `pythonic-builder` template generates module-level `@action`, `@guard`, `@service` decorated functions (no `self` parameter) and a `build()` function that uses the `MachineBuilder` fluent API to construct the machine.

### Command

```bash
xsm gt checkout.json --template pythonic-builder --async-mode no
```

### Generated Logic File: `checkout_logic.py`

```python
from typing import Any, Dict
from xstate_statemachine import (
    MachineBuilder,
    SyncInterpreter,
    action,
    guard,
    service,
)
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------

@action
def calculate_total(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Action handler for ``calculateTotal``."""
    logger.info("Executing action: calculateTotal")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Error in action calculateTotal")
        raise

@action
def clear_cart(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Action handler for ``clearCart``."""
    logger.info("Executing action: clearCart")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Error in action clearCart")
        raise

@action
def show_error(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Action handler for ``showError``."""
    logger.info("Executing action: showError")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Error in action showError")
        raise

# -----------------------------------------------------------------------
# Guards
# -----------------------------------------------------------------------

@guard
def cart_not_empty(
    context: Dict[str, Any],
    event: Any,
) -> bool:
    """Guard for ``cartNotEmpty``."""
    logger.info("Evaluating guard: cartNotEmpty")
    # TODO: implement guard logic
    return True

# -----------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------

@service
def process_payment(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
) -> Dict[str, Any]:
    """Service handler for ``processPayment``."""
    logger.info("Running service: processPayment")
    try:
        # TODO: implement service logic
        return {"result": "done"}
    except Exception:
        logger.exception("Error in service processPayment")
        raise


def build() -> Any:
    """Build the checkout machine using MachineBuilder."""
    machine = (
        MachineBuilder("checkout")
        .context({'items': [], 'total': 0})
        .state("cart", initial=True)
        .state("payment", invoke={'src': 'processPayment', 'onDone': {'target': 'confirmed', 'actions': 'clearCart'}, 'onError': {'target': 'cart', 'actions': 'showError'}})
        .state("confirmed")
        .transition("cart", "SUBMIT", "payment", actions=["calculateTotal"], guard="cartNotEmpty")
        .action("calculateTotal", calculate_total)
        .action("clearCart", clear_cart)
        .action("showError", show_error)
        .guard("cartNotEmpty", cart_not_empty)
        .service("processPayment", process_payment)
        .build()
    )
    return machine
```

### Generated Runner File: `checkout_runner.py`

```python
import logging
from xstate_statemachine import SyncInterpreter

import checkout_logic

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Executes the simulation for the checkout machine."""

    machine = checkout_logic.build()

    # Interpreter Setup
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f'Initial state: {interpreter.current_state_ids}')

    # Event Simulation
    logger.info('Sending event: %s', 'SUBMIT')
    interpreter.send("SUBMIT")

    interpreter.stop()

if __name__ == "__main__":
    main()
```

> **Key Feature:** The runner calls `checkout_logic.build()`, which uses the `MachineBuilder` fluent chain internally. Functions are registered by name via `.action("calculateTotal", calculate_total)`.

---

## Template 3: `pythonic-functional`

The `pythonic-functional` template generates module-level decorated functions and a `build()` function that creates `State` objects, calls `.to()` for transitions, and assembles the machine with `build_machine()`.

### Command

```bash
xsm gt checkout.json --template pythonic-functional --async-mode no
```

### Generated Logic File: `checkout_logic.py`

```python
from typing import Any, Dict
from xstate_statemachine import (
    State,
    build_machine,
    SyncInterpreter,
    action,
    guard,
    service,
)
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------

@action
def calculate_total(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Action handler for ``calculateTotal``."""
    logger.info("Executing action: calculateTotal")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Error in action calculateTotal")
        raise

@action
def clear_cart(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Action handler for ``clearCart``."""
    logger.info("Executing action: clearCart")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Error in action clearCart")
        raise

@action
def show_error(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Action handler for ``showError``."""
    logger.info("Executing action: showError")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Error in action showError")
        raise

# -----------------------------------------------------------------------
# Guards
# -----------------------------------------------------------------------

@guard
def cart_not_empty(
    context: Dict[str, Any],
    event: Any,
) -> bool:
    """Guard for ``cartNotEmpty``."""
    logger.info("Evaluating guard: cartNotEmpty")
    # TODO: implement guard logic
    return True

# -----------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------

@service
def process_payment(
    interpreter: SyncInterpreter,
    context: Dict[str, Any],
    event: Any,
) -> Dict[str, Any]:
    """Service handler for ``processPayment``."""
    logger.info("Running service: processPayment")
    try:
        # TODO: implement service logic
        return {"result": "done"}
    except Exception:
        logger.exception("Error in service processPayment")
        raise


def build() -> Any:
    """Build the checkout machine using build_machine()."""
    cart = State("cart", initial=True)
    payment = State("payment", invoke={'src': 'processPayment', 'onDone': {'target': 'confirmed', 'actions': 'clearCart'}, 'onError': {'target': 'cart', 'actions': 'showError'}})
    confirmed = State("confirmed")

    cart.to(payment, event="SUBMIT", actions="calculateTotal", guard="cartNotEmpty")

    machine = build_machine(
        id="checkout",
        states=[cart, payment, confirmed],
        context={'items': [], 'total': 0},
        actions=[calculate_total, clear_cart, show_error],
        guards=[cart_not_empty],
        services=[process_payment],
    )
    return machine
```

### Generated Runner File: `checkout_runner.py`

```python
import logging
from xstate_statemachine import SyncInterpreter

import checkout_logic

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Executes the simulation for the checkout machine."""

    machine = checkout_logic.build()

    # Interpreter Setup
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f'Initial state: {interpreter.current_state_ids}')

    # Event Simulation
    logger.info('Sending event: %s', 'SUBMIT')
    interpreter.send("SUBMIT")

    interpreter.stop()

if __name__ == "__main__":
    main()
```

> **Key Feature:** The `build()` function creates individual `State` objects, wires transitions with `.to()`, and calls `build_machine()` — the most explicit functional approach with function references passed directly.

---

## Template 4: `class-json`

The `class-json` template generates a class-based logic provider with method stubs. **The JSON config is loaded at runtime** — the machine definition stays in JSON. The `LogicLoader` auto-discovers methods by matching `snake_case` function names to `camelCase` JSON names.

### Command

```bash
xsm gt checkout.json --template class-json --async-mode no
```

### Generated Logic File: `checkout_logic.py`

```python
from typing import Any, Dict, Union
from xstate_statemachine import (
    Interpreter,
    SyncInterpreter,
    Event,
    ActionDefinition,
)
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Class-based Logic
# -----------------------------------------------------------------------

class CheckoutLogic:

    # Actions
    def calculate_total(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,
    ) -> None:
        """
        Action handler for ``calculateTotal``.

        Implement the business logic for this action.
        """
        try:
            logger.info("Executing action calculateTotal")
            # TODO: implement
        except Exception:
            logger.exception("Error in action calculateTotal")
            raise

    def clear_cart(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,
    ) -> None:
        """
        Action handler for ``clearCart``.

        Implement the business logic for this action.
        """
        try:
            logger.info("Executing action clearCart")
            # TODO: implement
        except Exception:
            logger.exception("Error in action clearCart")
            raise

    def show_error(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,
    ) -> None:
        """
        Action handler for ``showError``.

        Implement the business logic for this action.
        """
        try:
            logger.info("Executing action showError")
            # TODO: implement
        except Exception:
            logger.exception("Error in action showError")
            raise

    # Guards
    def cart_not_empty(
        self,
        context: Dict[str, Any],
        event: Event,
    ) -> bool:
        """
        Guard for ``cartNotEmpty``.

        Return True to allow the transition, False to block.
        """
        logger.info("Evaluating guard cartNotEmpty")
        # TODO: implement guard logic
        return True

    # Services
    def process_payment(
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
    ) -> Dict[str, Any]:
        """
        Service handler for ``processPayment``.

        Return a dict that becomes the onDone event data.
        """
        try:
            logger.info("Running service processPayment")
            # TODO: implement service
            return {'result': 'done'}
        except Exception:
            logger.exception("Error in service processPayment")
            raise
```

### Generated Runner File: `checkout_runner.py`

```python
from pathlib import Path
import json
from xstate_statemachine import create_machine, SyncInterpreter
from xstate_statemachine import LoggingInspector
import logging

from checkout_logic import CheckoutLogic as LogicProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Executes the simulation for the checkout machine."""

    config_path = Path(r"checkout.json")
    if not config_path.is_absolute() and config_path.parent == Path('.'):
        here = Path(__file__).resolve().parent
        candidate = here / config_path.name
        config_path = candidate if candidate.exists() else here.parent / config_path.name
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Logic Binding
    logic_provider = LogicProvider()
    machine = create_machine(config, logic_providers=[logic_provider])

    # Interpreter Setup
    interpreter = SyncInterpreter(machine)
    interpreter.use(LoggingInspector())
    interpreter.start()
    logger.info(f'Initial state: {interpreter.current_state_ids}')

    # Event Simulation
    logger.info('Sending event: %s', 'SUBMIT')
    interpreter.send('SUBMIT')

    interpreter.stop()

if __name__ == '__main__':
    main()
```

> **Key Feature:** The runner loads `checkout.json` at runtime and binds logic via `logic_providers=[LogicProvider()]`. The `LogicLoader` auto-discovers methods matching `snake_case` to `camelCase`.

---

## Template 5: `function-json`

The `function-json` template generates module-level function stubs (no class wrapper). **The JSON config is loaded at runtime**, and logic is bound via `logic_modules=[module]`.

### Command

```bash
xsm gt checkout.json --template function-json --async-mode no
```

### Generated Logic File: `checkout_logic.py`

```python
from typing import Any, Dict, Union
from xstate_statemachine import (
    Interpreter,
    SyncInterpreter,
    Event,
    ActionDefinition,
)
import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------

def calculate_total(
    interpreter: Union[Interpreter, SyncInterpreter],
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Action handler for ``calculateTotal``.

    Implement the business logic for this action.
    """
    try:
        logger.info("Executing action calculateTotal")
        # TODO: implement
    except Exception:
        logger.exception("Error in action calculateTotal")
        raise

def clear_cart(
    interpreter: Union[Interpreter, SyncInterpreter],
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Action handler for ``clearCart``.

    Implement the business logic for this action.
    """
    try:
        logger.info("Executing action clearCart")
        # TODO: implement
    except Exception:
        logger.exception("Error in action clearCart")
        raise

def show_error(
    interpreter: Union[Interpreter, SyncInterpreter],
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Action handler for ``showError``.

    Implement the business logic for this action.
    """
    try:
        logger.info("Executing action showError")
        # TODO: implement
    except Exception:
        logger.exception("Error in action showError")
        raise

# -----------------------------------------------------------------------
# Guards
# -----------------------------------------------------------------------

def cart_not_empty(
    context: Dict[str, Any],
    event: Event,
) -> bool:
    """
    Guard for ``cartNotEmpty``.

    Return True to allow the transition, False to block.
    """
    logger.info("Evaluating guard cartNotEmpty")
    # TODO: implement guard logic
    return True

# -----------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------

def process_payment(
    interpreter: Union[Interpreter, SyncInterpreter],
    context: Dict[str, Any],
    event: Event,
) -> Dict[str, Any]:
    """
    Service handler for ``processPayment``.

    Return a dict that becomes the onDone event data.
    """
    try:
        logger.info("Running service processPayment")
        # TODO: implement service
        return {'result': 'done'}
    except Exception:
        logger.exception("Error in service processPayment")
        raise
```

### Generated Runner File: `checkout_runner.py`

```python
from pathlib import Path
import json
from xstate_statemachine import create_machine, SyncInterpreter
from xstate_statemachine import LoggingInspector
import logging

import checkout_logic

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Executes the simulation for the checkout machine."""

    config_path = Path(r"checkout.json")
    if not config_path.is_absolute() and config_path.parent == Path('.'):
        here = Path(__file__).resolve().parent
        candidate = here / config_path.name
        config_path = candidate if candidate.exists() else here.parent / config_path.name
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Logic Binding
    machine = create_machine(config, logic_modules=[checkout_logic])

    # Interpreter Setup
    interpreter = SyncInterpreter(machine)
    interpreter.use(LoggingInspector())
    interpreter.start()
    logger.info(f'Initial state: {interpreter.current_state_ids}')

    # Event Simulation
    logger.info('Sending event: %s', 'SUBMIT')
    interpreter.send('SUBMIT')

    interpreter.stop()

if __name__ == '__main__':
    main()
```

> **Key Feature:** Logic binding uses `logic_modules=[checkout_logic]` — the `LogicLoader` scans the module for functions whose `snake_case` names match the `camelCase` names in JSON.

---

## Template Comparison Table

| Feature | `pythonic-class` | `pythonic-builder` | `pythonic-functional` | `class-json` | `function-json` |
|---------|:---:|:---:|:---:|:---:|:---:|
| JSON needed at runtime | No | No | No | Yes | Yes |
| Logic in a class | Yes (`StateMachine`) | No | No | Yes (provider) | No |
| Uses decorators | `@action`, `@guard`, `@service` | `@action`, `@guard`, `@service` | `@action`, `@guard`, `@service` | No | No |
| Type hints | Full | Full | Full | Full | Full |
| OOP pattern | Subclass | Builder | Functional | Provider | Module |
| `self` parameter | Yes | No | No | Yes | No |
| Machine creation | `MyMachine.create_machine()` | `build()` via `MachineBuilder` | `build()` via `build_machine()` | `create_machine(cfg, logic_providers=...)` | `create_machine(cfg, logic_modules=...)` |
| Best for large machines | Excellent | Excellent | Good | Excellent | Good |
| Name auto-mapping | snake_case → camelCase | snake_case → camelCase | snake_case → camelCase | snake_case via `LogicLoader` | snake_case via `LogicLoader` |
| Error handling in stubs | try/except | try/except | try/except | try/except | try/except |
| Default async mode | sync | sync | sync | async | async |

## When to Use Each Template

### Use `pythonic-class` when:
- You prefer a single, self-contained class that defines your entire machine
- You want the most Pythonic, declarative API
- You don't need to keep JSON files around after generation
- Your team is comfortable with OOP and decorators

### Use `pythonic-builder` when:
- You want module-level functions without class overhead
- You need to dynamically assemble machines (e.g., add states conditionally)
- You prefer the fluent builder pattern
- You want to keep logic functions decoupled from the machine structure

### Use `pythonic-functional` when:
- You want the simplest, most explicit machine construction
- You prefer functional programming style
- You want full control over `State` objects and `build_machine()` arguments
- Your machine is relatively straightforward

### Use `class-json` when:
- You have existing JSON configs from Stately.ai that you want to keep as source of truth
- You want to update the JSON without regenerating Python code
- You prefer organizing logic as methods on a class
- Your workflow involves frequent JSON config changes

### Use `function-json` when:
- You have existing JSON configs and want minimal code overhead
- You prefer flat module-level functions over classes
- You want the lightest-weight generated code
- You're prototyping or building quick scripts
