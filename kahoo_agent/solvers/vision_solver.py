"""
Multimodal Vision Solver for Kahoot games where questions are displayed on a host screen.
"""

import hashlib
import logging
import time
from typing import Callable, Optional
from PIL import Image

from ..ai.engine import get_ai_engine
from ..config import Settings
from ..models import AnswerResult, GameState, Option
from ..utils.screen import capture_screen, click_color_button
from .base import BaseSolver

logger = logging.getLogger("kahoo_agent.solvers.vision")


class VisionSolver(BaseSolver):
    """Solves Kahoot by observing a screen region (e.g. Zoom/Teams/Projector) with Gemini Vision."""

    def __init__(
        self,
        settings: Settings,
        on_answer_calculated: Optional[Callable[[AnswerResult], None]] = None,
        on_status_update: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(settings, on_status_update)
        self.on_answer_calculated = on_answer_calculated
        self.ai_engine = get_ai_engine(settings.ai)
        self.last_image_hash = ""
        self.last_solve_time = 0.0

    def start(self):
        """Starts monitoring the screen for questions."""
        self.is_running = True
        self.log("Vision Solver started. Monitoring screen for Kahoot questions...")

        poll_interval = self.settings.vision.poll_interval_sec
        roi = self.settings.vision.roi

        try:
            while self.is_running:
                screenshot = capture_screen(roi)
                img_hash = self._compute_image_hash(screenshot)

                # Avoid re-analyzing identical screens within 5 seconds
                now = time.time()
                if img_hash != self.last_image_hash and (now - self.last_solve_time > 4.0):
                    self.log("Screen change detected. Sending frame to Gemini Vision...")
                    self.current_state = GameState.QUESTION_ACTIVE

                    result = self.ai_engine.solve_vision(screenshot)
                    self.last_image_hash = img_hash
                    self.last_solve_time = now

                    if self.on_answer_calculated:
                        self.on_answer_calculated(result)

                    # Delay simulation
                    delay = self.settings.gameplay.answer_delay_sec
                    if delay > 0:
                        time.sleep(delay)

                    # Auto click
                    if self.settings.gameplay.mode == "auto":
                        chosen_indices = result.decision.selected_indices
                        if chosen_indices:
                            idx = chosen_indices[0]
                            self.log(f"Auto-clicking option [{idx}] ({Option.from_index(idx).color.value})...")
                            click_color_button(idx)

                    self.current_state = GameState.ANSWER_SENT

                time.sleep(poll_interval)
        except KeyboardInterrupt:
            self.log("Vision Solver interrupted by user.")
        finally:
            self.stop()

    def _compute_image_hash(self, img: Image.Image) -> str:
        """Fast low-res hash for visual change detection."""
        thumb = img.resize((32, 32)).convert("L")
        return hashlib.md5(thumb.tobytes()).hexdigest()

    def stop(self):
        self.is_running = False
        self.log("Vision Solver stopped.")
