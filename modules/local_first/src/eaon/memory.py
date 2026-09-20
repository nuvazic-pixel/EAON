from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import Claim


TOKEN_RE = re.compile(r"[\w-]{3,}", re.UNICODE)


class LocalMemory:
    """Inspectable, exportable SQLite memory. No network calls."""

    def __init__(self, path: str | Path = "data/eaon.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, path TEXT NOT NULL,
                    sha256 TEXT NOT NULL UNIQUE, ingested_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL REFERENCES sources(id),
                    text TEXT NOT NULL, evidence TEXT NOT NULL,
                    confidence REAL NOT NULL, tags_json TEXT NOT NULL,
                    normalized TEXT NOT NULL,
                    UNIQUE(source_id, normalized)
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, goal TEXT NOT NULL, result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def has_source_hash(self, digest: str) -> bool:
        with self.connect() as db:
            return db.execute("SELECT 1 FROM sources WHERE sha256 = ?", (digest,)).fetchone() is not None

    def add_source(self, source_id: str, title: str, path: str, digest: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO sources(id,title,path,sha256,ingested_at) VALUES(?,?,?,?,?)",
                (source_id, title, path, digest, datetime.now(timezone.utc).isoformat()),
            )

    def add_claims(self, claims: list[Claim]) -> int:
        inserted = 0
        with self.connect() as db:
            for claim in claims:
                normalized = " ".join(claim.text.lower().split())
                cursor = db.execute(
                    "INSERT OR IGNORE INTO claims(source_id,text,evidence,confidence,tags_json,normalized) VALUES(?,?,?,?,?,?)",
                    (claim.source_id, claim.text, claim.evidence, claim.confidence, json.dumps(claim.tags), normalized),
                )
                inserted += cursor.rowcount
        return inserted

    def search_claims(self, query: str, limit: int = 8) -> list[Claim]:
        terms = {token.lower() for token in TOKEN_RE.findall(query)}
        with self.connect() as db:
            rows = db.execute("SELECT * FROM claims").fetchall()
        ranked = []
        for row in rows:
            haystack = f"{row['text']} {row['evidence']} {' '.join(json.loads(row['tags_json']))}".lower()
            overlap = sum(1 for term in terms if term in haystack)
            if overlap:
                ranked.append((overlap, row))
        ranked.sort(key=lambda pair: (pair[0], pair[1]["confidence"]), reverse=True)
        return [
            Claim(
                id=row["id"], text=row["text"], source_id=row["source_id"],
                evidence=row["evidence"], confidence=row["confidence"],
                tags=json.loads(row["tags_json"]),
            )
            for _, row in ranked[:limit]
        ]

    def save_run(self, run_id: str, goal: str, result: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO runs(id,goal,result_json,created_at) VALUES(?,?,?,?)",
                (run_id, goal, json.dumps(result, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
            )

    def stats(self) -> dict[str, int]:
        with self.connect() as db:
            return {
                "sources": db.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
                "claims": db.execute("SELECT COUNT(*) FROM claims").fetchone()[0],
                "runs": db.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
            }

    def export_json(self, destination: str | Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            payload = {
                "sources": [dict(row) for row in db.execute("SELECT * FROM sources")],
                "claims": [dict(row) for row in db.execute("SELECT * FROM claims")],
                "runs": [dict(row) for row in db.execute("SELECT * FROM runs")],
            }
        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return destination
