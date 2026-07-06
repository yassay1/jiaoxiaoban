import pytest
from app.utils.json_utils import safe_json_loads, extract_json_text


class TestExtractJsonText:
    def test_none_raises(self):
        with pytest.raises(ValueError, match="返回 None"):
            extract_json_text(None, source="test")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="返回空字符串"):
            extract_json_text("", source="test")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="返回空字符串"):
            extract_json_text("   ", source="test")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="不是字符串"):
            extract_json_text(123, source="test")

    def test_standard_json(self):
        result = extract_json_text('{"key": "value"}', source="test")
        assert result == '{"key": "value"}'

    def test_markdown_json_block(self):
        raw = '```json\n{"key": "value"}\n```'
        result = extract_json_text(raw, source="test")
        assert result == '{"key": "value"}'

    def test_markdown_no_lang_block(self):
        raw = '```\n{"key": "value"}\n```'
        result = extract_json_text(raw, source="test")
        assert result == '{"key": "value"}'

    def test_json_with_explanatory_text(self):
        raw = '好的，我来分析：\n{"key": "value"}\n以上就是结果。'
        result = extract_json_text(raw, source="test")
        assert result == '{"key": "value"}'

    def test_json_with_nested_braces(self):
        raw = '{"outer": {"inner": [1, 2, 3]}}'
        result = extract_json_text(raw, source="test")
        assert result == '{"outer": {"inner": [1, 2, 3]}}'


class TestSafeJsonLoads:
    def test_standard_json(self):
        result = safe_json_loads('{"key": "value"}', source="test")
        assert result == {"key": "value"}

    def test_markdown_json_block(self):
        raw = '```json\n{"key": "value"}\n```'
        result = safe_json_loads(raw, source="test")
        assert result == {"key": "value"}

    def test_json_with_text_prefix(self):
        raw = '好的，分析如下：\n{"route": "direct_chat", "intent": "hello"}'
        result = safe_json_loads(raw, source="test")
        assert result == {"route": "direct_chat", "intent": "hello"}

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="返回空字符串"):
            safe_json_loads("", source="test")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="返回 None"):
            safe_json_loads(None, source="test")

    def test_non_json_text_raises(self):
        with pytest.raises(ValueError, match="不是合法 JSON"):
            safe_json_loads("这是普通文本，不是JSON", source="test")

    def test_incomplete_json_raises(self):
        with pytest.raises(ValueError, match="不是合法 JSON"):
            safe_json_loads('{"key": "value"', source="test")
