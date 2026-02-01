import pytest

from app.providers.gemini import GeminiProvider


def test_gemini_requires_cookie_path():
    with pytest.raises(ValueError):
        GeminiProvider(cookie_path="")
