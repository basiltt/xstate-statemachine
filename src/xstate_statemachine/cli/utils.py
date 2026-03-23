# src/xstate_statemachine/cli/utils.py
# -----------------------------------------------------------------------------
# 🛠️ CLI Utility Functions
# -----------------------------------------------------------------------------
# This module provides miscellaneous utility functions used across the CLI
# package. These are pure, self-contained helpers that perform common tasks
# like string case conversion and boolean normalization, promoting code reuse
# and adhering to the DRY (Don't Repeat Yourself) principle.
# -----------------------------------------------------------------------------
"""
Utility functions for the xstate-statemachine CLI.
"""

import re


def camel_to_snake(name: str) -> str:
    """Converts a string from camelCase or PascalCase to snake_case.

    This is a pure function used for normalizing machine and logic names to
    adhere to Python's PEP 8 naming conventions.  It also sanitizes the
    result so that it is always a valid Python identifier (spaces, hyphens,
    dots, and other non-alphanumeric characters are replaced with
    underscores, leading digits are prefixed with ``_``, and consecutive /
    trailing underscores are collapsed).

    Args:
        name (str): The string in camelCase or PascalCase.

    Returns:
        str: The converted string in snake_case that is a valid Python
        identifier.
    """
    # 1. Standard camelCase / PascalCase -> snake_case
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
    # 2. Replace any non-alphanumeric characters (spaces, hyphens, dots,
    #    parentheses, colons, etc.) with underscores
    name = re.sub(r"[^a-z0-9]+", "_", name)
    # 3. Strip leading/trailing underscores and collapse multiples
    name = re.sub(r"_+", "_", name).strip("_")
    # 4. Ensure the name doesn't start with a digit
    if name and name[0].isdigit():
        name = f"_{name}"
    # 5. Fallback for completely empty names
    if not name:
        name = "machine"
    return name


def normalize_bool(value: str) -> bool:
    """Normalizes a string representation of a boolean to a bool.

    This function handles common string values for true/false (e.g., "yes",
    "no", "1", "0") in a case-insensitive manner. It's used to parse CLI
    arguments that represent boolean flags.

    Args:
        value (str): The string to normalize.

    Returns:
        bool: The corresponding boolean value.

    Raises:
        ValueError: If the input string is not a recognized boolean value.
    """
    true_values = {"true", "yes", "y", "1"}
    false_values = {"false", "no", "n", "0"}
    lower_val = value.lower()

    if lower_val in true_values:
        return True
    if lower_val in false_values:
        return False

    raise ValueError(f"Invalid boolean value: '{value}'")
