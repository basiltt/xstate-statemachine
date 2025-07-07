# src/xstate_statemachine/logger.py
import logging

# -----------------------------------------------------------------------------
# 🪵 Library-Safe Logger Configuration
# -----------------------------------------------------------------------------
# This setup follows the best practice for logging in a reusable library.
#
# 1. We get a logger specific to this library's namespace.
# 2. We do NOT configure it with handlers or formatting, as that is the
#    responsibility of the end-user's application.
# 3. We add a `NullHandler` to prevent "No handler found" warnings if the
#    user's application has not configured logging. This handler is a no-op;
#    it does nothing with the log records.
# -----------------------------------------------------------------------------

# ✅ Get the top-level logger for the "xstate_statemachine" library.
logger = logging.getLogger("xstate_statemachine")

# ✅ Add a NullHandler to suppress "No handler found" warnings.
logger.addHandler(logging.NullHandler())
