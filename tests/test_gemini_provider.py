import json

import pytest

from app.providers.gemini import GeminiProvider


def test_gemini_requires_cookie_path():
    with pytest.raises(ValueError):
        GeminiProvider(cookie_path="")


def test_load_cookie_values(tmp_path):
    cookie_file = tmp_path / "gemini.json"
    cookie_file.write_text(
        json.dumps({"__Secure-1PSID": "psid", "__Secure-1PSIDTS": "psidts"}),
        encoding="utf-8",
    )
    psid, psidts = GeminiProvider.load_cookie_values(str(cookie_file))
    assert psid == "psid"
    assert psidts == "psidts"
