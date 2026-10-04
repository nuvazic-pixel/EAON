import pytest

from core.adaptive import AdaptiveModelPolicy, TaskEnvelope


def test_local_privacy_always_stays_local():
    route = AdaptiveModelPolicy().select(
        TaskEnvelope("private memory query", complexity=0.99, privacy_level="local")
    )
    assert route.tier == "local"
    assert route.reason == "privacy=local"


def test_low_complexity_routes_to_luna():
    route = AdaptiveModelPolicy().select(TaskEnvelope("extract fields", complexity=0.20))
    assert route.tier == "luna"
    assert route.require_verification is False


def test_medium_complexity_routes_to_sol():
    route = AdaptiveModelPolicy().select(TaskEnvelope("debug code", complexity=0.60))
    assert route.tier == "sol"
    assert route.require_verification is False


def test_high_complexity_requires_verification():
    route = AdaptiveModelPolicy().select(TaskEnvelope("engineering analysis", complexity=0.90))
    assert route.tier == "sol"
    assert route.require_verification is True


def test_evidence_flag_forces_verification_on_low_complexity():
    route = AdaptiveModelPolicy().select(
        TaskEnvelope("extract evidence", complexity=0.10, evidence_required=True)
    )
    assert route.tier == "luna"
    assert route.require_verification is True


@pytest.mark.parametrize("complexity", [-0.01, 1.01])
def test_invalid_complexity_rejected(complexity):
    with pytest.raises(ValueError):
        TaskEnvelope("bad", complexity=complexity)


def test_invalid_thresholds_rejected():
    with pytest.raises(ValueError):
        AdaptiveModelPolicy(low_threshold=0.8, high_threshold=0.2)
