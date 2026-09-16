"""
Prompt templates optimized for ultra-low latency Kahoot trivia solving.
"""

from typing import List
from ..models import Option, Question, QuestionType


QUIZ_SYSTEM_PROMPT = """You are a championship Kahoot trivia player AI.
Your goal is to identify the correct answer to the question with maximum speed and accuracy.

CRITICAL INSTRUCTIONS:
1. Return ONLY a valid, minified JSON object. Do not include markdown codeblocks (no ```json).
2. The JSON schema must strictly be:
{"answer_index": <int 0-3>, "confidence": <float 0.0-1.0>, "reason": "<max 10 words>"}
3. If multiple answers are allowed, use:
{"answer_indices": [<int>, ...], "confidence": <float>, "reason": "<max 10 words>"}
4. If it is an open-ended question, use:
{"text_answer": "<exact text>", "confidence": <float>, "reason": "<max 10 words>"}
5. Be concise. Speed is critical."""


VISION_SYSTEM_PROMPT = """You are an expert Kahoot visual solver watching a host screen.
Analyze the provided screenshot carefully:
1. Identify the question text.
2. Identify the 4 answer choices corresponding to the 4 colors:
   - 0: RED / Triangle
   - 1: BLUE / Diamond
   - 2: YELLOW / Circle
   - 3: GREEN / Square
3. Determine the correct answer.
4. Output ONLY a valid minified JSON object:
{"answer_index": <int 0-3>, "selected_color": "<red|blue|yellow|green>", "confidence": <float 0.0-1.0>, "reason": "<max 10 words>"}"""


def build_quiz_prompt(question: Question) -> str:
    """Builds a compact prompt representation of a question and its options."""
    lines = [f"Question: {question.text}"]

    if question.question_type == QuestionType.TRUE_FALSE:
        lines.append("Type: True/False")
    elif question.question_type == QuestionType.MULTI_SELECT:
        lines.append("Type: Multi-Select (Pick all correct answers)")

    if question.options:
        lines.append("Options:")
        for opt in question.options:
            lines.append(f"[{opt.index}] ({opt.color.value}/{opt.shape.value}): {opt.text}")

    lines.append("Response JSON:")
    return "\n".join(lines)


def build_vision_prompt() -> str:
    """Builds prompt for analyzing host screen screenshot."""
    return "Look at this Kahoot question on the host screen. Identify the question, examine the 4 colored options (0=Red, 1=Blue, 2=Yellow, 3=Green), and output the JSON with the correct answer_index."
