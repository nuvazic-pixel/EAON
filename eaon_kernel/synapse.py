"""Authenticated read-only Synapse bridge; no generated answers or memory writes."""
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .contracts import EvidenceCandidate, SourceRef, ValidationError, text


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SynapseEvidenceProvider:
    def __init__(self, base_url, token, owner_id, *, allow_remote=False, transport=None):
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValidationError("Invalid Synapse URL")
        try:
            local = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            local = parsed.hostname == "localhost"
        if not local and (not allow_remote or parsed.scheme != "https"):
            raise ValidationError("Synapse is loopback-only by default; remote access requires explicit HTTPS opt-in")
        self.base_url, self.owner_id = base_url.rstrip("/"), owner_id
        self.locality = "local" if local else "remote"
        self._token = text(token, "Synapse token", 20000)
        self._transport = transport or build_opener(ProxyHandler({}), _NoRedirect()).open

    def query(self, query, scope):
        text(query, "query", 2000)
        if scope.owner_id != self.owner_id or scope.collection_id is None:
            raise ValidationError("Synapse requires its configured owner and an explicit collection")
        if self.locality == "remote" and scope.privacy == "local":
            raise ValidationError("Privacy gate rejected remote retrieval")
        url = self.base_url + "/chat/evidence?" + urlencode({"q": query, "collection_id": scope.collection_id})
        request = Request(url, headers={"Authorization": "Bearer " + self._token, "Accept": "application/json"}, method="GET")
        try:
            with self._transport(request, timeout=10) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValidationError("Synapse response exceeded its size limit")
            payload = json.loads(raw)
        except HTTPError as exc:
            raise ValidationError(f"Synapse evidence request failed (HTTP {exc.code})") from None
        except (URLError, OSError, ValueError) as exc:
            raise ValidationError("Synapse evidence response is unavailable or invalid") from exc
        required = {"schema_version": "eaon.evidence.v1", "query": query, "owner_id": scope.owner_id,
                    "collection_id": scope.collection_id, "cache": "bypassed", "authority": "candidate_only"}
        if type(payload) is not dict or any(payload.get(k) != v for k, v in required.items()):
            raise ValidationError("Synapse response scope or evidence contract mismatch")
        try:
            stamp = datetime.fromisoformat(payload["retrieved_at"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValidationError("Synapse retrieval timestamp is missing or malformed") from exc
        if stamp.tzinfo is None or not -30 <= (datetime.now(timezone.utc) - stamp).total_seconds() <= 300:
            raise ValidationError("Synapse response has an invalid or stale retrieval time")
        if type(payload.get("results")) is not list or len(payload["results"]) > 100:
            raise ValidationError("Invalid Synapse evidence array")
        output = []
        for doc in payload["results"]:
            if type(doc) is not dict or not {"chunk_id", "document_id", "text", "sha256"} <= set(doc):
                raise ValidationError("Synapse evidence item is malformed")
            text(doc["chunk_id"], "chunk ID", 500)
            text(doc["document_id"], "document ID", 500)
            uri = "synapse://" + quote(scope.collection_id, safe="") + "/" + quote(doc["document_id"], safe="") + "#" + quote(doc["chunk_id"], safe="")
            source = SourceRef(doc["document_id"] + ":" + doc["chunk_id"], uri, doc["text"], doc["sha256"])
            output.append(EvidenceCandidate(source, "synapse", scope.owner_id, scope.collection_id,
                          doc.get("score"), expires_at=(stamp + timedelta(minutes=5)).isoformat(), retrieved_at=stamp.isoformat()))
        return output
