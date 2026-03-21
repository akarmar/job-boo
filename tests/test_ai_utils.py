"""Tests for AI utility functions (extract_json)."""

from __future__ import annotations

from job_boo.ai.utils import extract_json


class TestExtractJson:
    def test_fenced_json_block(self) -> None:
        text = 'Here is the result:\n```json\n{"score": 75}\n```\nDone.'
        assert extract_json(text) == '{"score": 75}'

    def test_fenced_block_without_json_tag(self) -> None:
        text = 'Result:\n```\n{"score": 75}\n```'
        assert extract_json(text) == '{"score": 75}'

    def test_no_fences_bare_json(self) -> None:
        text = '{"score": 75}'
        assert extract_json(text) == '{"score": 75}'

    def test_json_embedded_in_text(self) -> None:
        text = 'The analysis shows {"score": 75, "matched": true} and more text.'
        result = extract_json(text)
        assert '"score": 75' in result
        assert '"matched": true' in result

    def test_malformed_json_returns_stripped(self) -> None:
        text = "No JSON here at all"
        assert extract_json(text) == "No JSON here at all"

    def test_empty_string(self) -> None:
        assert extract_json("") == ""

    def test_whitespace_only(self) -> None:
        assert extract_json("   \n\t  ") == ""

    def test_multiple_code_blocks_returns_first(self) -> None:
        text = '```json\n{"first": 1}\n```\nAnd another:\n```json\n{"second": 2}\n```'
        assert extract_json(text) == '{"first": 1}'

    def test_fenced_with_leading_whitespace(self) -> None:
        text = '```json\n  {"score": 42}  \n```'
        assert extract_json(text) == '{"score": 42}'

    def test_nested_json_objects(self) -> None:
        text = '{"outer": {"inner": "value"}}'
        result = extract_json(text)
        assert '"outer"' in result
        assert '"inner"' in result

    def test_json_with_array(self) -> None:
        text = '```json\n{"skills": ["python", "java"]}\n```'
        result = extract_json(text)
        assert '"skills"' in result

    def test_curly_braces_at_different_positions(self) -> None:
        text = "Some prefix text { incomplete"
        # rfind('}') would not find a match after the {
        result = extract_json(text)
        assert result == "Some prefix text { incomplete"

    def test_text_with_only_opening_brace(self) -> None:
        text = "starts with { but never closes"
        result = extract_json(text)
        # No closing brace, so it falls through to strip
        assert result == text.strip()

    def test_braces_in_wrong_order(self) -> None:
        text = "} before { is wrong"
        # end < start, so falls through
        result = extract_json(text)
        assert result == text.strip()

    def test_multiline_json_in_fences(self) -> None:
        text = """```json
{
    "score": 85,
    "matched_skills": [
        "python",
        "aws"
    ],
    "reasoning": "Good match"
}
```"""
        result = extract_json(text)
        assert '"score": 85' in result
        assert '"reasoning"' in result
