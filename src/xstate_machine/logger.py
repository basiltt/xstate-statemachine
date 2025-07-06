### 3. `src/xstate_machine/logger.py`

# This file sets up the centralized logger


# src/xstate_machine/logger.py
import logging

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# A centralized logger to be used across the library. This allows users of the
# library to easily control the log level and output.
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("xstate_machine")
