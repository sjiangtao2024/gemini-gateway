from app.providers.base import BaseProvider


def test_provider_name_property():
    class Dummy(BaseProvider):
        name = "dummy"

        async def chat_completions(self, *args, **kwargs):
            return {}

        async def list_models(self):
            return []

    assert Dummy().name == "dummy"
