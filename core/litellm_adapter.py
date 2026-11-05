"""Optional LiteLLM proxy transport for EAON's exact-ID InferenceGateway.

No implicit model fallback. The EAON router remains the authority for selecting
logical model IDs; LiteLLM only executes the explicitly configured mapping.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Mapping

from .inference_gateway import InferenceGateway, ModelDispatchError


class LiteLLMProxyAdapter:
    def __init__(self, *, base_url: str = "http://127.0.0.1:4000",
                 model_map: Mapping[str, str], api_key: str | None = None,
                 timeout: float = 30.0) -> None:
        if not base_url.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
            raise ValueError("proxy_url_must_be_loopback_or_https")
        if not model_map or any(not k or not v for k, v in model_map.items()):
            raise ValueError("invalid_model_map")
        self.base_url = base_url.rstrip("/")
        self.model_map = dict(model_map)
        self.api_key = api_key
        self.timeout = timeout

    def handler(self, logical_model_id: str):
        if logical_model_id not in self.model_map:
            raise ModelDispatchError("unknown_model_id")
        proxy_model = self.model_map[logical_model_id]

        def invoke(prompt: str) -> str:
            payload = json.dumps({"model": proxy_model, "messages": [
                {"role": "user", "content": prompt}
            ]}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            req = urllib.request.Request(
                self.base_url + "/v1/chat/completions", data=payload,
                headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    data = json.load(response)
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ModelDispatchError("empty_model_response")
                return content
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError,
                    IndexError, TypeError) as exc:
                if isinstance(exc, ModelDispatchError):
                    raise
                raise ModelDispatchError("litellm_proxy_failure") from exc
        return invoke

    def gateway(self) -> InferenceGateway:
        return InferenceGateway({
            model_id: self.handler(model_id) for model_id in self.model_map
        })
