"""Tests for validation utilities."""

import pytest

from pm_mcp.core.validation import (
    ALLOWED_METADATA_KEYS,
    JIRA_ISSUE_KEY_PATTERN,
    MAX_MESSAGE_LENGTH,
    ValidationError,
    sanitize_user_input,
    validate_issue_keys,
    validate_metadata_dict,
)


class TestValidateIssueKeys:
    """Tests for validate_issue_keys function."""

    def test_valid_keys(self) -> None:
        """Test validation of valid issue keys."""
        keys = ["ALPHA-123", "BETA-1", "GAMMA-999"]
        result = validate_issue_keys(keys)
        assert result == keys

    def test_filters_invalid_keys(self) -> None:
        """Test filtering of invalid keys while keeping valid ones."""
        keys = ["ALPHA-123", "invalid", "BETA-", "-123", "alpha-123", "GAMMA-456"]
        result = validate_issue_keys(keys)
        assert result == ["ALPHA-123", "GAMMA-456"]

    def test_raises_on_all_invalid(self) -> None:
        """Test error when all keys invalid."""
        with pytest.raises(ValidationError, match="No valid issue keys found"):
            validate_issue_keys(["invalid", "bad-format", "123-ABC"])

    def test_empty_list_returns_empty(self) -> None:
        """Test that empty list returns empty list."""
        assert validate_issue_keys([]) == []

    def test_filters_non_strings(self) -> None:
        """Test that non-string values are filtered out."""
        keys = ["ALPHA-123", 123, None, "BETA-456"]  # type: ignore[list-item]
        result = validate_issue_keys(keys)
        assert result == ["ALPHA-123", "BETA-456"]

    def test_filters_too_long_keys(self) -> None:
        """Test that keys exceeding max length are filtered."""
        long_key = "A" * 51 + "-123"
        keys = ["ALPHA-123", long_key, "BETA-456"]
        result = validate_issue_keys(keys)
        assert result == ["ALPHA-123", "BETA-456"]

    def test_valid_pattern_variations(self) -> None:
        """Test various valid patterns."""
        keys = [
            "A-1",  # Minimal
            "AB-123",  # Two letters
            "ABC-999",  # Three letters
            "A1-100",  # Letter + digit in project
            "ABC123-999",  # Multiple chars
        ]
        result = validate_issue_keys(keys)
        assert result == keys


class TestSanitizeUserInput:
    """Tests for sanitize_user_input function."""

    def test_removes_control_chars(self) -> None:
        """Test removal of control characters."""
        text = "Hello\x00World\x1FTest"
        result = sanitize_user_input(text)
        assert "\x00" not in result
        assert "\x1F" not in result
        assert "HelloWorldTest" == result

    def test_preserves_newlines_and_tabs(self) -> None:
        """Test that newlines and tabs are preserved."""
        text = "Line1\nLine2\tTabbed"
        result = sanitize_user_input(text)
        assert "\n" in result
        assert "\t" in result

    def test_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        text = "  \n  Content  \t\n  "
        result = sanitize_user_input(text)
        assert result == "Content"

    def test_raises_on_too_long(self) -> None:
        """Test error on messages exceeding size limit."""
        text = "x" * (MAX_MESSAGE_LENGTH + 1)
        with pytest.raises(ValidationError, match="Message too long"):
            sanitize_user_input(text)

    def test_raises_on_empty(self) -> None:
        """Test error on empty input."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            sanitize_user_input("")

    def test_raises_on_whitespace_only(self) -> None:
        """Test error when only whitespace/control chars remain."""
        text = "  \t\n\x00\x1F  "
        with pytest.raises(ValidationError, match="only whitespace"):
            sanitize_user_input(text)

    def test_normal_text_unchanged(self) -> None:
        """Test that normal text passes through unchanged (except trim)."""
        text = "  Normal text with spaces and punctuation!  "
        result = sanitize_user_input(text)
        assert result == "Normal text with spaces and punctuation!"

    def test_unicode_preserved(self) -> None:
        """Test that Unicode characters are preserved."""
        text = "Привет мир! 你好世界"
        result = sanitize_user_input(text)
        assert result == text

    def test_exactly_max_length_ok(self) -> None:
        """Test that exactly max length is allowed."""
        text = "x" * MAX_MESSAGE_LENGTH
        result = sanitize_user_input(text)
        assert len(result) == MAX_MESSAGE_LENGTH


class TestValidateMetadataDict:
    """Tests for validate_metadata_dict function."""

    def test_filters_unknown_keys(self) -> None:
        """Test filtering of unknown metadata keys."""
        data = {
            "jira_project_key": "ALPHA",
            "unknown_key": "value",
            "confluence_space_key": "SPACE",
            "another_unknown": "test",
        }
        result = validate_metadata_dict(data)
        assert "unknown_key" not in result
        assert "another_unknown" not in result
        assert result["jira_project_key"] == "ALPHA"
        assert result["confluence_space_key"] == "SPACE"

    def test_converts_values_to_strings(self) -> None:
        """Test that values are converted to strings."""
        data = {
            "jira_project_key": 123,  # type: ignore[dict-item]
            "version": 1.0,  # type: ignore[dict-item]
        }
        result = validate_metadata_dict(data)
        assert result["jira_project_key"] == "123"
        assert result["version"] == "1.0"

    def test_filters_none_values(self) -> None:
        """Test that None values are filtered out."""
        data = {
            "jira_project_key": "ALPHA",
            "confluence_space_key": None,
            "version": "v1",
        }
        result = validate_metadata_dict(data)
        assert "confluence_space_key" not in result
        assert "jira_project_key" in result
        assert "version" in result

    def test_empty_dict_returns_empty(self) -> None:
        """Test that empty dict returns empty dict."""
        assert validate_metadata_dict({}) == {}

    def test_only_allowed_keys_in_output(self) -> None:
        """Test that result only contains allowed keys."""
        data = {"jira_project_key": "ALPHA", "bad_key": "value"}
        result = validate_metadata_dict(data)
        for key in result:
            assert key in ALLOWED_METADATA_KEYS


class TestJiraIssueKeyPattern:
    """Tests for JIRA_ISSUE_KEY_PATTERN regex."""

    def test_valid_patterns(self) -> None:
        """Test that valid patterns match."""
        valid_keys = [
            "A-1",
            "AB-123",
            "ABC-999",
            "PROJ-1234567",
            "A1-1",
            "AB2C3-99",
        ]
        for key in valid_keys:
            assert JIRA_ISSUE_KEY_PATTERN.match(key), f"Should match: {key}"

    def test_invalid_patterns(self) -> None:
        """Test that invalid patterns don't match."""
        invalid_keys = [
            "abc-123",  # Lowercase
            "-123",  # Missing project
            "ABC-",  # Missing number
            "ABC",  # Missing separator and number
            "ABC_123",  # Wrong separator
            "123-ABC",  # Number first
            "A BC-123",  # Space in project
            "",  # Empty
        ]
        for key in invalid_keys:
            assert not JIRA_ISSUE_KEY_PATTERN.match(key), f"Should not match: {key}"
