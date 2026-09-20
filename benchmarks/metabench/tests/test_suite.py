from eaon_metabench.suites import generate_metacognition_suite


def test_suite_is_reproducible() -> None:
    first = generate_metacognition_suite(count=12, seed=7)
    second = generate_metacognition_suite(count=12, seed=7)
    assert [case.case_id for case in first] == [case.case_id for case in second]
    assert [case.prompt for case in first] == [case.prompt for case in second]


def test_suite_covers_all_categories() -> None:
    cases = generate_metacognition_suite(count=12, seed=7)
    categories = {case.category for case in cases}
    assert categories == {
        "insufficient_information",
        "contradiction_detection",
        "rule_shift",
        "error_repair",
    }
