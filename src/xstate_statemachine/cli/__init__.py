# src/xstate_statemachine/cli/__init__.py
# -----------------------------------------------------------------------------
# 🏛️ Command-Line Interface (CLI) Package
# -----------------------------------------------------------------------------
# This package encapsulates all functionality for the command-line interface
# of the xstate-statemachine library. It is responsible for parsing arguments,
# processing machine configurations, and generating boilerplate code.
#
# By structuring the CLI as a package, we adhere to the Single Responsibility
# Principle, separating concerns into dedicated modules:
#   - __main__.py: The main entry point and orchestration logic.
#   - args.py: Defines and parses all command-line arguments.
#   - extractor.py: Handles the extraction of data (actions, guards, etc.)
#                   from JSON configuration files.
#   - generator.py: Contains the core logic for generating Python source code.
#   - utils.py: Provides common utility functions.
# -----------------------------------------------------------------------------
"""
xstate-statemachine Command-Line Interface (CLI) package.
"""

from .__main__ import main

__all__ = ["main"]
