# tests/tests_cli/base.py
# -----------------------------------------------------------------------------
# 🏛️ Base Test Case for CLI File Operations
# -----------------------------------------------------------------------------
# This module provides the `CLITestCaseBase` class, a foundational test case
# for all CLI tests that interact with the filesystem. It embodies the
# "Template Method" design pattern for test setup and teardown.
#
# By creating and cleaning up a temporary working directory for each test,
# it ensures that file-based tests are completely isolated and do not have
# side effects, promoting test reliability and atomicity.
# -----------------------------------------------------------------------------
"""
Defines a base class for CLI tests requiring filesystem interaction.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import os
import tempfile
import unittest

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Base Test Class
# -----------------------------------------------------------------------------


class CLITestCaseBase(unittest.TestCase):
    """
    A base class for CLI tests that creates a temporary directory.

    This class handles the boilerplate of creating a temporary directory before
    each test and cleaning it up afterward, ensuring a pristine environment
    for file generation and output verification.
    """

    temp_dir: tempfile.TemporaryDirectory
    original_cwd: str

    def setUp(self) -> None:
        """
        Set up a temporary directory and change the current working directory to it.
        """
        # ⚙️ Create a new temporary directory for this test run.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        logger.info(
            "🚀 Setting up test environment in: %s", self.temp_dir.name
        )

    def tearDown(self) -> None:
        """
        Clean up the temporary directory and restore the original working directory.
        """
        # 🧹 Restore the original working directory.
        os.chdir(self.original_cwd)
        # 🗑️ Cleanly remove the temporary directory and all its contents.
        self.temp_dir.cleanup()
        logger.info("✅ Tearing down test environment: %s", self.temp_dir.name)
