from adapters.openai_responses import MODEL_BY_TIER, _extract_output_text


def test_model_tiers_use_current_gpt6_ids():
    assert MODEL_BY_TIER["luna"] == "gpt-6-luna"
    assert MODEL_BY_TIER["sol"] == "gpt-6-sol"


def test_extract_output_text_from_response_items():
    payload = {
        "output": [
            {"content": [{"type": "output_text", "text": "hello "}]},
            {"content": [{"type": "output_text", "text": "world"}]},
        ]
    }
    assert _extract_output_text(payload) == "hello world"


def test_direct_output_text_is_supported():
    assert _extract_output_text({"output_text": "ok"}) == "ok"
