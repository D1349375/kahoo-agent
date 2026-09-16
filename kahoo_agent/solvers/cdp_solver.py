"""
CDP Browser Automation Solver using Playwright.
Connects directly to an existing Chrome instance on remote debugging port 9222.
"""

import logging
import time
from typing import Callable, List, Optional
from playwright.sync_api import Page, sync_playwright

from ..ai.engine import get_ai_engine
from ..config import Settings
from ..models import AnswerResult, GameState, Option, Question, QuestionType
from .base import BaseSolver

logger = logging.getLogger("kahoo_agent.solvers.cdp")


class CDPSolver(BaseSolver):
    """Solves Kahoot games by attaching to a live Chrome browser via Chrome DevTools Protocol."""

    def __init__(
        self,
        settings: Settings,
        on_question_detected: Optional[Callable[[Question], None]] = None,
        on_answer_calculated: Optional[Callable[[AnswerResult], None]] = None,
        on_status_update: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(settings, on_status_update)
        self.on_question_detected = on_question_detected
        self.on_answer_calculated = on_answer_calculated
        self.ai_engine = get_ai_engine(settings.ai)
        self.playwright = None
        self.browser = None
        self.page: Optional[Page] = None
        self.last_answered_question_key = ""

    def connect(self) -> bool:
        """Establishes connection to the remote Chrome instance via CDP."""
        cdp_url = self.settings.browser.cdp_url
        self.log(f"Connecting to browser CDP endpoint at {cdp_url}...")
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)

            # Find Kahoot tab
            keyword = self.settings.browser.target_url_keyword
            for context in self.browser.contexts:
                for p in context.pages:
                    if keyword in p.url:
                        self.page = p
                        self.log(f"Attached to Kahoot player tab: {p.url} (Title: '{p.title()}')")
                        return True

            # If not found immediately, check the first active page or wait
            if self.browser.contexts and self.browser.contexts[0].pages:
                self.page = self.browser.contexts[0].pages[0]
                self.log(f"Warning: No explicit '{keyword}' tab found. Using active tab: {self.page.url}")
                return True

            self.log(f"Error: No browser tabs found on {cdp_url}. Please open kahoot.it in Chrome.")
            return False
        except Exception as e:
            self.log(f"Failed to connect to CDP: {e}")
            logger.error(f"CDP connection failed: {e}", exc_info=True)
            return False

    def start(self):
        """Starts the continuous monitoring and solving loop."""
        if not self.connect():
            return

        self.is_running = True
        self.log("CDP Solver running. Waiting for game questions...")

        try:
            while self.is_running:
                try:
                    self._tick()
                except Exception as e:
                    logger.debug(f"Tick error: {e}")
                time.sleep(0.15)
        except KeyboardInterrupt:
            self.log("Received keyboard interrupt.")
        finally:
            self.stop()

    def _tick(self):
        """Single polling cycle to inspect game state and react."""
        if not self.page or self.page.is_closed():
            return

        # 1. Check if an active answer pad is visible
        answer_buttons = self._find_answer_buttons()
        if not answer_buttons:
            self.current_state = GameState.QUESTION_WAITING
            return

        # 2. Extract question text and options
        question = self._extract_question_data(len(answer_buttons))
        question_key = f"{question.text}_{len(question.options)}"

        # Avoid double-submitting the same question in one round
        if question_key == self.last_answered_question_key:
            return

        self.current_state = GameState.QUESTION_ACTIVE
        if self.on_question_detected:
            self.on_question_detected(question)

        # 3. AI Reasoning
        self.log(f"Question detected: '{question.text or '(Text on Host Screen)'}'")
        answer_result = self.ai_engine.solve_question(question)

        if self.on_answer_calculated:
            self.on_answer_calculated(answer_result)

        # 4. Human-like or configured answer delay
        delay = self.settings.gameplay.answer_delay_sec
        if delay > 0:
            time.sleep(delay)

        # 5. Submit answer if auto mode is enabled
        if self.settings.gameplay.mode == "auto":
            self._click_answer(answer_result, answer_buttons)

        self.last_answered_question_key = question_key
        self.current_state = GameState.ANSWER_SENT

    def _find_answer_buttons(self) -> List[any]:
        """Finds interactive answer buttons currently rendered on screen."""
        selectors = [
            'button[data-functional-selector^="answer-"]',
            'button[data-functional-selector^="question-choice-"]',
            '[data-functional-selector="multi-select-submit-button"]',
        ]
        for sel in selectors:
            locators = self.page.locator(sel).all()
            if locators:
                return locators
        return []

    def _extract_question_data(self, button_count: int) -> Question:
        """Extracts available question metadata from DOM."""
        q_text = ""
        q_selectors = [
            '[data-functional-selector="block-title"]',
            '[data-functional-selector="question-title"]',
            'h1',
            'h2',
        ]
        for sel in q_selectors:
            loc = self.page.locator(sel)
            if loc.count() > 0:
                text = loc.first.inner_text().strip()
                if text:
                    q_text = text
                    break

        # Check options
        options = []
        for i in range(button_count):
            opt_text = ""
            # Try to find option text inside button if enabled by host
            try:
                btn_loc = self.page.locator(f'button[data-functional-selector="answer-{i}"]')
                if btn_loc.count() > 0:
                    t = btn_loc.first.inner_text().strip()
                    if t:
                        opt_text = t
            except Exception:
                pass
            options.append(Option.from_index(i, opt_text))

        q_type = QuestionType.TRUE_FALSE if button_count == 2 else QuestionType.QUIZ
        return Question(
            text=q_text if q_text else "Kahoot Question",
            question_type=q_type,
            options=options,
        )

    def _click_answer(self, result: AnswerResult, buttons: List[any]):
        """Executes click on the chosen answer button."""
        indices = result.decision.selected_indices
        if not indices:
            indices = [0]

        for idx in indices:
            if idx < len(buttons):
                try:
                    self.log(f"Clicking option [{idx}] (Color/Shape: {Option.from_index(idx).color.value})...")
                    buttons[idx].click(timeout=1000)
                except Exception as e:
                    self.log(f"Failed to click button {idx}: {e}")

    def stop(self):
        """Disconnects and cleans up Playwright resources."""
        self.is_running = False
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
        self.log("CDP Solver stopped.")
