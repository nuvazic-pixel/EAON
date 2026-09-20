from app.core.config import get_settings


class DomainExcludedError(ValueError):
    pass


def enforce_personal_twin_policy(domain: str) -> None:
    """Reject raw work/professional data from the personal Cognitive Twin.

    If a useful cognitive pattern originated at work, rewrite it as a sanitized
    cognitive observation first and ingest that observation under domain='cognitive'.
    """
    settings = get_settings()
    normalized = domain.strip().lower()
    if normalized in settings.excluded_domain_set:
        raise DomainExcludedError(
            f"Domain '{domain}' is excluded by Personal Twin policy. "
            "Store only a sanitized cognitive observation, not workplace details."
        )
