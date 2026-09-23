"""Model registry for adaptive EAON tiers."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str


class ModelRegistry:
    """Resolve logical tiers to provider/model pairs without coupling policy to IDs."""

    DEFAULTS = {
        "low": ModelSpec("openai", "gpt-6-luna"),
        "high": ModelSpec("openai", "gpt-6-sol"),
        "local": ModelSpec("ollama", "llama3"),
    }

    ENV_KEYS = {
        "low": "EAON_MODEL_LOW",
        "high": "EAON_MODEL_HIGH",
        "local": "EAON_MODEL_LOCAL",
    }

    def resolve(self, tier: str) -> ModelSpec:
        normalized = {"luna": "low", "sol": "high"}.get(tier.lower(), tier.lower())
        if normalized not in self.DEFAULTS:
            raise ValueError(f"unsupported model tier: {tier}")

        default = self.DEFAULTS[normalized]
        raw = os.getenv(self.ENV_KEYS[normalized], default.model).strip()
        if not raw:
            raise ValueError(f"empty model configuration for tier: {normalized}")

        if "/" in raw:
            provider, model = raw.split("/", 1)
            if not provider or not model:
                raise ValueError(f"invalid provider/model configuration: {raw}")
            return ModelSpec(provider.lower(), model)

        return ModelSpec(default.provider, raw)
