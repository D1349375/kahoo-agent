"""
Base Solver abstraction.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
from ..config import Settings
from ..models import AnswerResult, GameState, Question


class BaseSolver(ABC):
    """Abstract base class for all Kahoot solving strategies."""

    def __init__(self, settings: Settings, on_status_update: Optional[Callable[[str], None]] = None):
        self.settings = settings
        self.on_status_update = on_status_update
        self.is_running = False
        self.current_state = GameState.UNKNOWN

    def log(self, message: str):
        if self.on_status_update:
            self.on_status_update(message)

    @abstractmethod
    def start(self):
        """Starts the solver loop."""
        pass

    @abstractmethod
    def stop(self):
        """Stops the solver."""
        pass
