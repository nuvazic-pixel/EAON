"""Persistent SQLite store for EAON knowledge ingestion v0.1."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Iterable
from .claim_extractor import ExtractedClaim
from .openalex import OpenAlexWork

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS works (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, publication_year INTEGER,
 publication_date TEXT, doi TEXT, abstract TEXT, cited_by_count INTEGER NOT NULL DEFAULT 0,
 source_name TEXT, is_open_access INTEGER NOT NULL DEFAULT 0,
 topics_json TEXT NOT NULL DEFAULT '[]', referenced_works_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS claims (
 id TEXT PRIMARY KEY, work_id TEXT NOT NULL, text TEXT NOT NULL,
 evidence_text TEXT NOT NULL, publication_year INTEGER,
 topics_json TEXT NOT NULL DEFAULT '[]', extractor TEXT NOT NULL,
 confidence REAL NOT NULL,
 FOREIGN KEY(work_id) REFERENCES works(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_claims_work_id ON claims(work_id);
CREATE INDEX IF NOT EXISTS idx_claims_publication_year ON claims(publication_year);
"""

class KnowledgeStore:
    def __init__(self, path: str | Path = "data/eaon_knowledge.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()
    def __enter__(self) -> "KnowledgeStore":
        return self
    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def upsert_work(self, work: OpenAlexWork) -> None:
        self.connection.execute("""
        INSERT INTO works (id,title,publication_year,publication_date,doi,abstract,cited_by_count,source_name,is_open_access,topics_json,referenced_works_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title, publication_year=excluded.publication_year,
        publication_date=excluded.publication_date, doi=excluded.doi, abstract=excluded.abstract,
        cited_by_count=excluded.cited_by_count, source_name=excluded.source_name,
        is_open_access=excluded.is_open_access, topics_json=excluded.topics_json,
        referenced_works_json=excluded.referenced_works_json
        """, (work.id,work.title,work.publication_year,work.publication_date,work.doi,work.abstract,
              work.cited_by_count,work.source_name,int(work.is_open_access),json.dumps(work.topics,ensure_ascii=False),json.dumps(work.referenced_works)))

    def upsert_claim(self, claim: ExtractedClaim) -> None:
        self.connection.execute("""
        INSERT INTO claims (id,work_id,text,evidence_text,publication_year,topics_json,extractor,confidence)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET text=excluded.text,evidence_text=excluded.evidence_text,
        publication_year=excluded.publication_year,topics_json=excluded.topics_json,
        extractor=excluded.extractor,confidence=excluded.confidence
        """, (claim.claim_id,claim.source_id,claim.text,claim.evidence_text,claim.publication_year,
              json.dumps(claim.topics,ensure_ascii=False),claim.extractor,claim.confidence))

    def ingest(self, work: OpenAlexWork, claims: Iterable[ExtractedClaim]) -> int:
        self.upsert_work(work)
        count = 0
        for claim in claims:
            self.upsert_claim(claim)
            count += 1
        self.connection.commit()
        return count

    def stats(self) -> dict[str, int]:
        works = self.connection.execute("SELECT COUNT(*) FROM works").fetchone()[0]
        claims = self.connection.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        return {"works": works, "claims": claims}
