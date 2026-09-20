from eaon_metabench.models import BenchmarkCase, ModelAnswer
from eaon_metabench.scoring import answer_is_correct, confidence_calibration_score


def test_abstention_correctness() -> None:
    case = BenchmarkCase(
        case_id="x",
        category="insufficient_information",
        prompt="x",
        expected_decision="abstain",
    )
    answer = ModelAnswer(decision="abstain", answer="", confidence=0.9)
    assert answer_is_correct(case, answer)


def test_answer_normalization() -> None:
    case = BenchmarkCase(
        case_id="x",
        category="contradiction_detection",
        prompt="x",
        expected_decision="answer",
        accepted_answers=("INCONSISTENT",),
    )
    answer = ModelAnswer(decision="answer", answer="inconsistent.", confidence=0.9)
    assert answer_is_correct(case, answer)


def test_calibration_rewards_confident_correct_answer() -> None:
    assert confidence_calibration_score(0.95, True) > 0.99
    assert confidence_calibration_score(0.95, False) < 0.1
