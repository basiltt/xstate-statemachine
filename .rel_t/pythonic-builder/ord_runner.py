"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    ord.json
Template:  pythonic-builder
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template ord.json --template pythonic-builder

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""

import logging
import time
from xstate_statemachine import SyncInterpreter

import ord_logic

# -----------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main() -> None:
    """Executes the simulation for the ord machine."""

    machine = ord_logic.build()

    # Interpreter Setup
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f'Initial state: {interpreter.current_state_ids}')

    # Event Simulation
    logger.info('Sending event: %s', 'GO')
    interpreter.send("GO")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    interpreter.send("CANCEL")
    time.sleep(2)

    interpreter.stop()

if __name__ == "__main__":
    main()