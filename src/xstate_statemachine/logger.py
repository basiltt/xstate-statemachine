# /src/xstate_statemachine/logger.py
# -----------------------------------------------------------------------------
# 🪵 Library-Safe Logger Configuration
# -----------------------------------------------------------------------------
# This module sets up a library-specific logger that is safe for distribution.
# It follows the best practice outlined in the official Python documentation
# for configuring logging in reusable libraries.
#
# The key principles are:
#   1. Obtain a logger instance specific to this library's namespace.
#   2. Do NOT add handlers other than `NullHandler`. The end-user's
#      application is responsible for configuring the actual log handlers
#      (e.g., `StreamHandler`, `FileHandler`).
#   3. Add a `NullHandler` to prevent "No handler found" warnings if the
#      end-user's application has not configured logging at all.
#
# This approach ensures our library plays nicely in any environment without
# interfering with the application's own logging setup.
# -----------------------------------------------------------------------------
"""
Configures a library-level logger instance.

This module is responsible for creating a single, top-level logger for the
`xstate_statemachine` package. This allows all other modules in the library
to get a logger instance (e.g., `logging.getLogger(__name__)`) that will
inherit this base configuration.

By adding a `NullHandler`, we prevent unseemly `No handler found` error
messages from appearing in the console of an application that consumes this
library but has not configured its own logging. The `NullHandler` is a no-op
that simply discards any log records sent to it.

Example:
    How other modules in this library use the logger:

    >>> # In another file, e.g., interpreter.py
    >>> import logging
    >>>
    >>> # ✅ FIX: Renamed variable to `module_logger` to avoid shadowing.
    >>> # This logger inherits from the base logger configured here.
    >>> logger = logging.getLogger(__name__) # noqa
    >>>
    >>> def some_function():
    ...     # This log message will be handled by the application's
    ...     # logging config, or silently discarded by the NullHandler
    ...     # if no config exists.
    ...     logger.info("🚀 A function was called.")

"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging

# -----------------------------------------------------------------------------
# 🪵 Logger Initialization
# -----------------------------------------------------------------------------

# 🚀 Get the top-level logger for the entire "xstate_statemachine" library.
# All loggers created in submodules (e.g., logging.getLogger(__name__)) will
# be children of this logger, inheriting its settings.
logger = logging.getLogger("xstate_statemachine")

# 🔕 Add a NullHandler to the library's logger.
# This is the crucial step for being a "good citizen" library. It prevents
# `logging` from printing a "No handler found" error to stderr if the
# consuming application has not set up any logging handlers.
logger.addHandler(logging.NullHandler())
