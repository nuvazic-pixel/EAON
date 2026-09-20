from eaon_metabench.parsing import parse_model_answer


def test_parses_clean_json() -> None:
    answer, error = parse_model_answer(
        '{"decision":"answer","answer":"42","confidence":0.9,"reason":"math"}'
    )
    assert error is None
    assert answer is not None
    assert answer.answer == "42"


def test_extracts_json_from_fence() -> None:
    answer, error = parse_model_answer(
        '```json\n{"decision":"abstain","answer":"","confidence":0.8,"reason":"missing"}\n```'
    )
    assert error is None
    assert answer is not None
    assert answer.decision == "abstain"
