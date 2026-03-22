# src/xstate_statemachine/cli/strategies/base.py
"""Base strategy class and shared data structures."""

import dataclasses
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set


@dataclasses.dataclass
class GenerationContext:
    """All inputs needed by any strategy to generate code."""

    actions: Set[str]
    guards: Set[str]
    services: Set[str]
    is_async: bool
    log: bool
    machine_name: str
    machine_id: str
    machine_names: List[str]
    machine_ids: List[str]
    file_count: int
    configs: List[Dict[str, Any]]
    json_filenames: List[str]
    hierarchy: bool
    sleep: bool
    sleep_time: int
    loader: bool
    style: Optional[str] = None


class BaseStrategy(ABC):
    """Abstract base for code generation strategies."""

    @abstractmethod
    def generate_logic(self, ctx: GenerationContext) -> str:
        """Generate the logic/implementation code."""

    @abstractmethod
    def generate_runner(self, ctx: GenerationContext) -> str:
        """Generate the runner/execution code."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable template name."""
