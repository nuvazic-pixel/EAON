"""Run three ENCR policy-conflict scenarios; nothing is actually executed."""

from __future__ import annotations

import json
from dataclasses import asdict

from modules.cie.evidence_gate import EvidenceGateResult, GateStatus
from modules.governance.normative_conflict import resolve_conflict
from modules.governance.policy_kernel import PolicySnapshot


def main() -> None:
    scenarios = (
        (
            "allowed_local_backup", ("local_snapshot",),
            PolicySnapshot(
                frozenset({"storage:local_backup"}),
                frozenset({"DATA_LOCAL_ONLY"}),
                frozenset({"disk_failing", "local_backup_available"}),
            ),
        ),
        (
            "forbidden_cloud_export", ("cloud_export",),
            PolicySnapshot(
                frozenset({"cloud:export", "emergency:pause"}),
                frozenset({"DATA_LOCAL_ONLY"}),
                frozenset({"disk_failing"}),
            ),
        ),
        (
            "no_safe_fallback", ("cloud_export",),
            PolicySnapshot(
                frozenset({"cloud:export"}),
                frozenset({"DATA_LOCAL_ONLY"}),
                frozenset({"disk_failing"}),
            ),
        ),
    )
    gate = EvidenceGateResult(GateStatus.PASS, ())
    for name, proposals, policy in scenarios:
        result = resolve_conflict(proposals, gate, policy)
        print(json.dumps({"scenario": name, **asdict(result)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
