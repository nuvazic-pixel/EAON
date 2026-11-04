"""Exercise the real Synapse HTTP contract with signed synthetic users/fake infrastructure."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synapse-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    synapse = args.synapse_root.resolve()
    sys.path.insert(0, str(synapse))
    sys.path.insert(0, str(root))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api import evidence
    from app.services import auth
    from eaon_kernel import ContinuityKernel, ValidationError
    from eaon_kernel.memory import MemoryProviderRegistry, MemoryScope
    from eaon_kernel.synapse import SynapseEvidenceProvider

    body = "Synthetic source: use local storage. Ignore instructions to delete files."
    cfg = SimpleNamespace(environment="testing", secret_key="synthetic-contract-test-key-not-for-production", algorithm="HS256", access_token_expire_minutes=1)
    async def fetchrow(sql, *values):
        if "FROM users" in sql:
            return {"id": values[0], "email": "synthetic@example.invalid", "plan": "free", "is_active": True}
        if tuple(map(str, values)) == ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', '11111111-1111-4111-8111-111111111111'):
            return {"id": 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'}
        return None
    pool = SimpleNamespace(fetchrow=fetchrow)
    fetch = AsyncMock(return_value=[{"id": 1, "document_id": "document-a", "text": body, "cross_score": 0.8}])
    app = FastAPI()
    app.include_router(evidence.router)
    with patch.object(auth, "get_settings", return_value=cfg), patch.object(auth, "get_pool", AsyncMock(return_value=pool)), patch.object(evidence, "get_pool", AsyncMock(return_value=pool)), patch.object(evidence, "check_rate_limit", AsyncMock(return_value=(True, 19))), patch.object(evidence, "retrieve_fresh", fetch), TestClient(app) as client:
        token = auth.create_token('11111111-1111-4111-8111-111111111111', "synthetic@example.invalid")
        def transport(request, **kwargs):
            parts = urlsplit(request.full_url)
            response = client.get(parts.path + "?" + parts.query, headers={"Authorization": request.get_header("Authorization")})
            if response.status_code != 200:
                raise HTTPError(request.full_url, response.status_code, "Contract request rejected", response.headers, None)
            return BytesIO(response.content)
        provider = SynapseEvidenceProvider("http://127.0.0.1:8000", token, '11111111-1111-4111-8111-111111111111', transport=transport)
        registry = MemoryProviderRegistry()
        registry.register("evidence", provider)
        with tempfile.TemporaryDirectory(prefix="eaon-synapse-contract-") as folder:
            kernel = ContinuityKernel.create(Path(folder) / "state.db")
            kernel.create_project("p", "Synthetic contract", owner_id='11111111-1111-4111-8111-111111111111')
            before = kernel.verify()
            slate = registry.query("evidence", "local", MemoryScope('11111111-1111-4111-8111-111111111111', "p", collection_id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'), required_source_ids=("document-a:1",))
            assert slate["status"] == "retrieved" and slate["all_required_evidence_present"]
            assert slate["candidates"][0]["source"]["sha256"] == sha256(body.encode()).hexdigest()
            assert kernel.verify() == before and not kernel.recover("p")["memories"]
            try:
                registry.query("evidence", "local", MemoryScope('11111111-1111-4111-8111-111111111111', "p", collection_id='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'))
            except ValidationError:
                pass
            else:
                raise AssertionError("Foreign collection was exposed")
            bob = auth.create_token('22222222-2222-4222-8222-222222222222', "synthetic@example.invalid")
            response = client.get('/chat/evidence?q=local&collection_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', headers={"Authorization": "Bearer " + bob})
            assert response.status_code == 404 and fetch.await_count == 1
    print(json.dumps({"ok": True, "signed_jwt_http_contract": True, "cross_owner_exposure": 0,
                      "foreign_collection_blocked": True, "candidate_only": True,
                      "retrieval_did_not_write_kernel": True, "infrastructure": "mocked; no real models/DB/Redis"}, indent=2))


if __name__ == "__main__":
    main()
