from app.services.model_registry import ModelRegistry


def test_prefix_filtering():
    registry = ModelRegistry(prefixes=["qwen-"])
    models = registry.filter_models(["qwen-2.5", "gpt-4o"])
    assert models == ["qwen-2.5"]
