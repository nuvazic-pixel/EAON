"""Offline tests: no LiteLLM server or cloud account required."""
import json
import unittest
from unittest.mock import patch
from core.inference_gateway import ModelDispatchError
from core.litellm_adapter import LiteLLMProxyAdapter


class FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return b""


class LiteLLMAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = LiteLLMProxyAdapter(model_map={"local": "ollama/llama3"})
        self.gateway = self.adapter.gateway()

    def test_unknown_model_rejected_without_request(self):
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(ModelDispatchError):
                self.gateway.dispatch("unapproved", "hello")
            urlopen.assert_not_called()

    def test_exact_model_and_response(self):
        class Response(FakeResponse):
            def read(self, *args):
                return json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()
        with patch("urllib.request.urlopen", return_value=Response()) as urlopen:
            self.assertEqual(self.gateway.dispatch("local", "hello"), "OK")
            request = urlopen.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(payload["model"], "ollama/llama3")
            self.assertEqual(payload["messages"][0]["content"], "hello")

    def test_empty_response_fails_closed(self):
        class Response(FakeResponse):
            def read(self, *args):
                return json.dumps({"choices": [{"message": {"content": ""}}]}).encode()
        with patch("urllib.request.urlopen", return_value=Response()):
            with self.assertRaises(ModelDispatchError):
                self.gateway.dispatch("local", "hello")

    def test_no_implicit_fallback_on_network_failure(self):
        from urllib.error import URLError
        with patch("urllib.request.urlopen", side_effect=URLError("offline")) as urlopen:
            with self.assertRaisesRegex(ModelDispatchError, "litellm_proxy_failure"):
                self.gateway.dispatch("local", "hello")
            self.assertEqual(urlopen.call_count, 1)

    def test_reject_unencrypted_remote_proxy(self):
        with self.assertRaises(ValueError):
            LiteLLMProxyAdapter(base_url="http://remote.example:4000",
                                model_map={"local": "ollama/llama3"})


if __name__ == "__main__":
    unittest.main()
