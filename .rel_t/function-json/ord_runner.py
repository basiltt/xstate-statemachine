"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    ord.json
Template:  function-json
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template ord.json --template function-json

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""

from pathlib import Path
import json
from xstate_statemachine import create_machine, Interpreter
from xstate_statemachine import LoggingInspector
import logging
import asyncio

import ord_logic

# -----------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def main() -> None:
    """Executes the simulation for the ord machine."""

    config_path = Path(r"ord.json")
    if not config_path.is_absolute() and config_path.parent == Path('.'):
        here = Path(__file__).resolve().parent
        candidate = here / config_path.name
        config_path = (candidate if candidate.exists() else here.parent / config_path.name)
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Logic Binding
    machine = create_machine(config, logic_modules=[ord_logic])

    # Interpreter Setup
    interpreter = Interpreter(machine)
    interpreter.use(LoggingInspector())
    await interpreter.start()
    logger.info(f'Initial state: {interpreter.current_state_ids}')

    # Event Simulation
    logger.info('Sending event: %s', 'GO')
    await interpreter.send('GO')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    logger.info('Sending event: %s', 'CANCEL')
    await interpreter.send('CANCEL')
    await asyncio.sleep(2)

    await interpreter.stop()

if __name__ == '__main__':
    asyncio.run(main())