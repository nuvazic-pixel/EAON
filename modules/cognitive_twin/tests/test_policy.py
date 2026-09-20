import pytest

from app.services.policy import DomainExcludedError, enforce_personal_twin_policy


def test_personal_domain_is_allowed():
    enforce_personal_twin_policy("cognitive")


def test_work_domain_is_rejected():
    with pytest.raises(DomainExcludedError):
        enforce_personal_twin_policy("work")
