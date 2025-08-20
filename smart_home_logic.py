# -------------------------------------------------------------------------------
# 📡 Generated Logic File
# -------------------------------------------------------------------------------

import asyncio
from typing import Awaitable
from typing import Any, Dict, Union

from xstate_statemachine import (
    Interpreter,
    SyncInterpreter,
    Event,
    ActionDefinition,
)

import logging

# -----------------------------------------------------------------------------
# 🧾 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🧠 Class‑based Logic
# -----------------------------------------------------------------------------
class SmartHomeLogic:

    # ⚙️ Actions
    async def log_power_off(  # noqa: ignore IDE static method warning,
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa: D401 – lib callback
    ) -> Awaitable[None]:  # noqa : ignore IDE return type hint warning
        """Action: `logPowerOff`."""
        logger.info("Executing action logPowerOff")
        await asyncio.sleep(0.1)  # placeholder
        # TODO: implement

    async def log_power_on(  # noqa: ignore IDE static method warning,
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa: D401 – lib callback
    ) -> Awaitable[None]:  # noqa : ignore IDE return type hint warning
        """Action: `logPowerOn`."""
        logger.info("Executing action logPowerOn")
        await asyncio.sleep(0.1)  # placeholder
        # TODO: implement

    # 🔄 Services
    async def light_bulb(  # noqa: ignore IDE static method warning,
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
    ) -> Awaitable[
        Dict[str, Any]
    ]:  # noqa : ignore IDE return type hint warning
        """Service: `LightBulb`."""
        logger.info("Running service LightBulb")
        await asyncio.sleep(1)
        # TODO: implement service
        return {"result": "done"}  # noqa : ignore IDE return type hint warning

    LightBulb = light_bulb  # alias for JSON name

    async def thermostat(  # noqa: ignore IDE static method warning,
        self,
        interpreter: Union[Interpreter, SyncInterpreter],
        context: Dict[str, Any],
        event: Event,
    ) -> Awaitable[
        Dict[str, Any]
    ]:  # noqa : ignore IDE return type hint warning
        """Service: `Thermostat`."""
        logger.info("Running service Thermostat")
        await asyncio.sleep(1)
        # TODO: implement service
        return {"result": "done"}  # noqa : ignore IDE return type hint warning

    Thermostat = thermostat  # alias for JSON name
