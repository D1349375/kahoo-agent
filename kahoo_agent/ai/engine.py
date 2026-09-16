"""
AI Reasoning Engine supporting Google Gemini API with fallback mechanisms.
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from PIL import Image

from ..config import AIConfig
from ..models import AnswerDecision, AnswerResult, Option, Question, QuestionType
from .prompts import QUIZ_SYSTEM_PROMPT, VISION_SYSTEM_PROMPT, build_quiz_prompt, build_vision_prompt

logger = logging.getLogger("kahoo_agent.ai")


class BaseAIEngine:
    """Base class for AI solvers."""

    def solve_question(self, question: Question) -> AnswerResult:
        raise NotImplementedError

    def solve_vision(self, image: Image.Image) -> AnswerResult:
        raise NotImplementedError


class GeminiAIEngine(BaseAIEngine):
    """Google Gemini AI engine optimized for low latency and high accuracy."""

    def __init__(self, config: AIConfig):
        self.config = config
        self.client = None
        self._setup_client()

    def _setup_client(self):
        """Initializes the Gemini client."""
        if not self.config.api_key:
            logger.warning("No GEMINI_API_KEY provided. AI engine will operate in mock mode.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.config.model_name or "gemini-2.5-flash",
                generation_config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": 128,
                    "response_mime_type": "application/json",
                },
                system_instruction=QUIZ_SYSTEM_PROMPT,
            )
            self.vision_model = genai.GenerativeModel(
                model_name=self.config.model_name or "gemini-2.5-flash",
                generation_config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": 128,
                    "response_mime_type": "application/json",
                },
                system_instruction=VISION_SYSTEM_PROMPT,
            )
            self.client = genai
            logger.info(f"Gemini client initialized with model: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize google.generativeai: {e}")
            self.client = None

    def solve_question(self, question: Question) -> AnswerResult:
        """Solves a text-based question extracted from Kahoot DOM."""
        start_time = time.perf_counter()

        if not self.client:
            # Fallback mock for testing
            return self._mock_solve(question, start_time)

        prompt = build_quiz_prompt(question)
        try:
            response = self.model.generate_content(prompt)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            raw_text = response.text.strip() if response and response.text else ""
            decision = self._parse_json_response(raw_text, question)
            return AnswerResult(
                decision=decision,
                latency_ms=latency_ms,
                raw_response=raw_text,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Gemini inference failed: {e}")
            return self._fallback_decision(question, latency_ms, str(e))

    def solve_vision(self, image: Image.Image) -> AnswerResult:
        """Solves a question by analyzing an image of the host screen."""
        start_time = time.perf_counter()

        if not self.client:
            return self._mock_vision_solve(image, start_time)

        prompt = build_vision_prompt()
        try:
            response = self.vision_model.generate_content([prompt, image])
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            raw_text = response.text.strip() if response and response.text else ""
            dummy_q = Question(text="Vision Screen Question", options=[Option.from_index(i) for i in range(4)])
            decision = self._parse_json_response(raw_text, dummy_q)
            return AnswerResult(
                decision=decision,
                latency_ms=latency_ms,
                raw_response=raw_text,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Gemini vision inference failed: {e}")
            dummy_q = Question(text="Vision Screen Question", options=[Option.from_index(i) for i in range(4)])
            return self._fallback_decision(dummy_q, latency_ms, str(e))

    def _parse_json_response(self, text: str, question: Question) -> AnswerDecision:
        """Parses json output from LLM, with fallback regex extraction."""
        clean_text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        clean_text = re.sub(r"```$", "", clean_text).strip()

        try:
            data = json.loads(clean_text)
            indices = []
            if "answer_index" in data and isinstance(data["answer_index"], int):
                indices = [data["answer_index"]]
            elif "answer_indices" in data and isinstance(data["answer_indices"], list):
                indices = [int(x) for x in data["answer_indices"]]

            confidence = float(data.get("confidence", 0.95))
            reasoning = str(data.get("reason", data.get("reasoning", "")))
            text_ans = data.get("text_answer")

            # Validate index bounds
            max_index = len(question.options) - 1 if question.options else 3
            valid_indices = [idx for idx in indices if 0 <= idx <= max_index]
            if not valid_indices:
                valid_indices = [0]

            return AnswerDecision(
                selected_indices=valid_indices,
                confidence=confidence,
                reasoning=reasoning,
                text_answer=text_ans,
            )
        except Exception:
            # Fallback regex search for a digit 0-3
            match = re.search(r"\b([0-3])\b", clean_text)
            chosen_idx = int(match.group(1)) if match else 0
            return AnswerDecision(
                selected_indices=[chosen_idx],
                confidence=0.5,
                reasoning="Regex fallback extraction",
            )

    def _mock_solve(self, question: Question, start_time: float) -> AnswerResult:
        """Deterministic mock solver for offline development."""
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return AnswerResult(
            decision=AnswerDecision(
                selected_indices=[0],
                confidence=0.99,
                reasoning="Mock: Default to option 0 (Red/Triangle)",
            ),
            latency_ms=latency_ms,
            raw_response='{"answer_index": 0, "confidence": 0.99, "reason": "Mock"}',
        )

    def _mock_vision_solve(self, image: Image.Image, start_time: float) -> AnswerResult:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return AnswerResult(
            decision=AnswerDecision(
                selected_indices=[1],
                confidence=0.88,
                reasoning="Mock Vision: Selected Blue/Diamond",
            ),
            latency_ms=latency_ms,
            raw_response='{"answer_index": 1, "selected_color": "blue", "confidence": 0.88}',
        )

    def _fallback_decision(self, question: Question, latency_ms: float, err: str) -> AnswerResult:
        return AnswerResult(
            decision=AnswerDecision(
                selected_indices=[0],
                confidence=0.25,
                reasoning=f"Inference error fallback: {err[:50]}",
            ),
            latency_ms=latency_ms,
            raw_response="",
        )


def get_ai_engine(config: AIConfig) -> BaseAIEngine:
    """Factory helper to obtain AI engine instance."""
    return GeminiAIEngine(config)
