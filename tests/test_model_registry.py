from core.model_registry import ModelRegistry


def test_defaults_resolve_logical_tiers(monkeypatch):
    for key in ("EAON_MODEL_LOW", "EAON_MODEL_HIGH", "EAON_MODEL_LOCAL"):
        monkeypatch.delenv(key, raising=False)
    registry = ModelRegistry()
    assert registry.resolve("low").model == "gpt-6-luna"
    assert registry.resolve("high").model == "gpt-6-sol"
    assert registry.resolve("local").provider == "ollama"


def test_env_can_override_provider_and_model(monkeypatch):
    monkeypatch.setenv("EAON_MODEL_LOW", "ollama/qwen2.5")
    spec = ModelRegistry().resolve("low")
    assert spec.provider == "ollama"
    assert spec.model == "qwen2.5"


def test_policy_aliases_are_supported():
    registry = ModelRegistry()
    assert registry.resolve("luna") == registry.resolve("low")
    assert registry.resolve("sol") == registry.resolve("high")
