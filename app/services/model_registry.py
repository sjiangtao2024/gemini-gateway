class ModelRegistry:
    def __init__(self, prefixes: list[str]):
        self.prefixes = prefixes

    def filter_models(self, models: list[str]) -> list[str]:
        if not self.prefixes:
            return models
        return [model for model in models if any(model.startswith(prefix) for prefix in self.prefixes)]
