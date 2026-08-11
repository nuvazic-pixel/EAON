"""OpenAlex ingestion adapter for EAON."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional
import requests

OPENALEX_API = "https://api.openalex.org"

@dataclass
class OpenAlexWork:
    id: str
    title: str
    publication_year: Optional[int] = None
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    abstract: str = ""
    cited_by_count: int = 0
    referenced_works: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    source_name: Optional[str] = None
    is_open_access: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

def reconstruct_abstract(inverted_index: Optional[dict[str, list[int]]]) -> str:
    if not inverted_index:
        return ""
    positioned = [(pos, token) for token, positions in inverted_index.items() for pos in positions]
    positioned.sort(key=lambda item: item[0])
    return " ".join(token for _, token in positioned)

class OpenAlexClient:
    def __init__(self, api_key: Optional[str] = None, mailto: Optional[str] = None, timeout: int = 30, session: Optional[requests.Session] = None) -> None:
        self.api_key = api_key or os.getenv("OPENALEX_API_KEY")
        self.mailto = mailto or os.getenv("OPENALEX_MAILTO")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "EAON-KnowledgeGapEngine/0.1"})

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        params = dict(params)
        if self.api_key:
            params["api_key"] = self.api_key
        if self.mailto:
            params["mailto"] = self.mailto
        response = self.session.get(f"{OPENALEX_API}{path}", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def normalize_work(payload: dict[str, Any]) -> OpenAlexWork:
        primary_location = payload.get("primary_location") or {}
        source = primary_location.get("source") or {}
        oa = payload.get("open_access") or {}
        topics = [t.get("display_name") for t in (payload.get("topics") or []) if t.get("display_name")]
        return OpenAlexWork(
            id=payload.get("id", ""),
            title=payload.get("display_name") or payload.get("title") or "",
            publication_year=payload.get("publication_year"),
            publication_date=payload.get("publication_date"),
            doi=payload.get("doi"),
            abstract=reconstruct_abstract(payload.get("abstract_inverted_index")),
            cited_by_count=int(payload.get("cited_by_count") or 0),
            referenced_works=list(payload.get("referenced_works") or []),
            topics=topics,
            source_name=source.get("display_name"),
            is_open_access=bool(oa.get("is_oa", False)),
            raw=payload,
        )

    def iter_works(self, query: str, *, from_year: Optional[int] = None, to_year: Optional[int] = None, max_works: int = 100, per_page: int = 100) -> Iterator[OpenAlexWork]:
        if max_works <= 0:
            return
        per_page = max(1, min(per_page, 200))
        filters: list[str] = []
        if from_year is not None:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year is not None:
            filters.append(f"to_publication_date:{to_year}-12-31")
        cursor = "*"
        yielded = 0
        while yielded < max_works:
            params: dict[str, Any] = {"search": query, "per-page": min(per_page, max_works-yielded), "cursor": cursor}
            if filters:
                params["filter"] = ",".join(filters)
            payload = self._request("/works", params)
            results = payload.get("results") or []
            if not results:
                break
            for raw_work in results:
                yield self.normalize_work(raw_work)
                yielded += 1
                if yielded >= max_works:
                    return
            next_cursor = (payload.get("meta") or {}).get("next_cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
