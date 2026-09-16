"""
Data models and enumerations for Kahoot game states, questions, and AI answers.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class KahootColor(str, Enum):
    RED = "red"
    BLUE = "blue"
    YELLOW = "yellow"
    GREEN = "green"


class KahootShape(str, Enum):
    TRIANGLE = "triangle"
    DIAMOND = "diamond"
    CIRCLE = "circle"
    SQUARE = "square"


# Standard Kahoot 4-option mapping by index
STANDARD_OPTIONS_MAP = [
    {"color": KahootColor.RED, "shape": KahootShape.TRIANGLE},
    {"color": KahootColor.BLUE, "shape": KahootShape.DIAMOND},
    {"color": KahootColor.YELLOW, "shape": KahootShape.CIRCLE},
    {"color": KahootColor.GREEN, "shape": KahootShape.SQUARE},
]


class QuestionType(str, Enum):
    QUIZ = "quiz"
    TRUE_FALSE = "boolean"
    MULTI_SELECT = "multiple"
    OPEN_ENDED = "open_ended"
    UNKNOWN = "unknown"


class Option(BaseModel):
    index: int = Field(description="Zero-based index of the option (0=Red, 1=Blue, 2=Yellow, 3=Green)")
    text: str = Field(default="", description="The text of the option if visible")
    color: KahootColor = Field(default=KahootColor.RED)
    shape: KahootShape = Field(default=KahootShape.TRIANGLE)

    @classmethod
    def from_index(cls, index: int, text: str = "") -> "Option":
        if 0 <= index < len(STANDARD_OPTIONS_MAP):
            spec = STANDARD_OPTIONS_MAP[index]
            return cls(index=index, text=text, color=spec["color"], shape=spec["shape"])
        return cls(index=index, text=text, color=KahootColor.RED, shape=KahootShape.TRIANGLE)


class Question(BaseModel):
    id: Optional[str] = None
    question_number: Optional[int] = None
    text: str = Field(description="The question prompt")
    question_type: QuestionType = Field(default=QuestionType.QUIZ)
    options: List[Option] = Field(default_factory=list)
    image_url: Optional[str] = None
    time_limit_sec: Optional[int] = None


class AnswerDecision(BaseModel):
    selected_indices: List[int] = Field(
        default_factory=list,
        description="List of selected option indices (0 to 3)",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(default="", description="Brief explanation of the answer")
    text_answer: Optional[str] = Field(default=None, description="For open-ended questions")


class AnswerResult(BaseModel):
    decision: AnswerDecision
    latency_ms: float = Field(default=0.0, description="Inference latency in milliseconds")
    raw_response: str = Field(default="", description="Raw response text from LLM")


class GameState(str, Enum):
    UNKNOWN = "unknown"
    PIN_INPUT = "pin_input"
    NICKNAME_INPUT = "nickname_input"
    LOBBY_WAITING = "lobby_waiting"
    GET_READY = "get_ready"
    QUESTION_ACTIVE = "question_active"
    ANSWER_SENT = "answer_sent"
    RESULT_FEEDBACK = "result_feedback"
    GAME_OVER = "game_over"
