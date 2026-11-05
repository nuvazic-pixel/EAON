# EAON + LiteLLM — experimental adapter

Status: **adapter and offline unit tests only**. Not wired into the existing
orchestrator, CLI or voice UI. No live proxy test has been performed.

The EAON deterministic router selects an authorized logical model ID.
`LiteLLMProxyAdapter` maps that ID to an explicitly configured LiteLLM
proxy model and returns a handler compatible with `InferenceGateway`.
Unknown IDs, empty replies and network failures fail closed. No automatic
fallback, retry, cost optimization or cloud permission is implied.

## Offline test

```powershell
py -3.12 -m unittest tests.test_litellm_adapter -v
```

## Optional local proxy configuration

Install LiteLLM Proxy in a separate Python environment or container,
pinning a tested version. Example `litellm_config.yaml`:

```yaml
model_list:
  - model_name: eaon-local
    litellm_params:
      model: ollama/llama3
      api_base: http://127.0.0.1:11434
```

Start a local LiteLLM Proxy on port 4000 according to its version-specific
documentation. Keep it bound to loopback and protect access before any remote
deployment. No cloud API keys are required for this local example.

## Standalone example

```python
from core.litellm_adapter import LiteLLMProxyAdapter

adapter = LiteLLMProxyAdapter(
    model_map={"llama3": "eaon-local"},
    base_url="http://127.0.0.1:4000",
)
answer = adapter.gateway().dispatch("llama3", "Hello EAON")
print(answer)
```

This is not yet an EAON end-to-end integration. Next: verify existing gateway
tests, test live loopback Ollama + LiteLLM, then wire behind an explicit
opt-in configuration flag. Never send personal memory to cloud models without
an explicit privacy gate. Keep existing Ollama path unchanged by default.
