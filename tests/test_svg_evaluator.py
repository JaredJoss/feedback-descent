import pytest

from feedback_descent.domains.svg.evaluator import _parse_judge_response


class TestParseJudgeResponse:
    def test_valid_json(self):
        response = '{"winner": "A", "rationale": "Image A has better composition", "feedback": "fix the legs"}'
        winner, rationale, feedback = _parse_judge_response(response)
        assert winner == "A"
        assert "better composition" in rationale
        assert "fix the legs" in feedback

    def test_json_with_surrounding_text(self):
        response = """After careful analysis:

{"winner": "B", "rationale": "Image B shows more detail and better color usage", "feedback": "add more detail"}

That's my assessment."""
        winner, rationale, feedback = _parse_judge_response(response)
        assert winner == "B"
        assert "more detail" in rationale

    def test_lowercase_winner(self):
        response = '{"winner": "a", "rationale": "A is better", "feedback": "improve shading"}'
        winner, rationale, feedback = _parse_judge_response(response)
        assert winner == "A"

    def test_winner_with_whitespace(self):
        response = '{"winner": " B ", "rationale": "B wins", "feedback": "fix proportions"}'
        winner, rationale, feedback = _parse_judge_response(response)
        assert winner == "B"

    def test_regex_fallback(self):
        # Malformed JSON but has the right pattern
        response = 'I think "winner": "A" and "rationale": "A is clearly better" and "feedback": "fix neck"'
        winner, rationale, feedback = _parse_judge_response(response)
        assert winner == "A"

    def test_no_parseable_response_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            _parse_judge_response("I can't decide, both are great!")

    def test_json_missing_rationale(self):
        response = '{"winner": "A"}'
        winner, rationale, feedback = _parse_judge_response(response)
        assert winner == "A"
        assert rationale == ""

    def test_feedback_defaults_to_rationale(self):
        response = '{"winner": "A", "rationale": "A has better anatomy"}'
        winner, rationale, feedback = _parse_judge_response(response)
        assert winner == "A"
        assert feedback == rationale
