"""Tests for lib.slug.slugify — feature-name → filesystem-safe slug."""
import re

from lib.slug import slugify


def test_pure_ascii_passthrough():
    assert slugify("user-login") == "user-login"


def test_ascii_with_spaces_to_hyphen():
    assert slugify("User Login Feature") == "user-login-feature"


def test_uppercase_normalized_to_lowercase():
    assert slugify("UserLogin") == "userlogin"


def test_chinese_falls_back_to_hash():
    """Chinese chars don't pinyin-romanize in v0.1; we use a stable hash + first ASCII chars if any."""
    result = slugify("用户登录功能")
    # No Chinese chars survive
    assert not re.search(r"[一-鿿]", result)
    # Stable: same input → same output
    assert slugify("用户登录功能") == result
    # Non-empty (8-char hash minimum)
    assert len(result) >= 8


def test_mixed_chinese_and_ascii():
    """Mixed input keeps ASCII portion + appends hash for the Chinese remainder."""
    result = slugify("用户 login 功能")
    assert "login" in result
    # And a hash suffix for stability
    assert re.search(r"-[a-f0-9]{6,}$", result)


def test_special_chars_stripped():
    assert slugify("foo/bar?baz!") == "foo-bar-baz"


def test_empty_string_raises():
    import pytest
    with pytest.raises(ValueError):
        slugify("")


def test_whitespace_only_raises():
    import pytest
    with pytest.raises(ValueError):
        slugify("   ")


def test_max_length_truncated():
    """v0.1: cap slug at 64 chars to avoid filesystem issues."""
    long_name = "a" * 200
    result = slugify(long_name)
    assert len(result) <= 64


def test_consecutive_hyphens_collapsed():
    assert slugify("foo---bar") == "foo-bar"


def test_leading_trailing_hyphens_stripped():
    assert slugify("--foo-bar--") == "foo-bar"
