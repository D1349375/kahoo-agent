"""
Unit tests for AI engine, models, and prompts.
"""

from kahoo_agent.config import AIConfig
from kahoo_agent.models import KahootColor, Option, Question, QuestionType
from kahoo_agent.ai.prompts import build_quiz_prompt
from kahoo_agent.ai.engine import GeminiAIEngine


def test_option_creation():
    opt = Option.from_index(0, "Answer 1")
    assert opt.color == KahootColor.RED
    assert opt.index == 0
    assert opt.text == "Answer 1"

    opt_blue = Option.from_index(1, "Answer 2")
    assert opt_blue.color == KahootColor.BLUE


def test_prompt_building():
    q = Question(
        text="What is 2 + 2?",
        question_type=QuestionType.QUIZ,
        options=[
            Option.from_index(0, "3"),
            Option.from_index(1, "4"),
            Option.from_index(2, "5"),
            Option.from_index(3, "6"),
        ],
    )
    prompt = build_quiz_prompt(q)
    assert "What is 2 + 2?" in prompt
    assert "[1] (blue/diamond): 4" in prompt


def test_mock_engine_solving():
    cfg = AIConfig(api_key=None)  # Triggers mock mode
    engine = GeminiAIEngine(cfg)

    q = Question(
        text="Test Question",
        options=[Option.from_index(i) for i in range(4)],
    )
    result = engine.solve_question(q)
    assert result.decision.selected_indices == [0]
    assert result.decision.confidence > 0.9
    assert result.latency_ms >= 0


def test_json_parsing():
    cfg = AIConfig(api_key=None)
    engine = GeminiAIEngine(cfg)
    q = Question(text="Test", options=[Option.from_index(i) for i in range(4)])

    parsed = engine._parse_json_response('{"answer_index": 2, "confidence": 0.92, "reason": "Accurate"}', q)
    assert parsed.selected_indices == [2]
    assert parsed.confidence == 0.92
