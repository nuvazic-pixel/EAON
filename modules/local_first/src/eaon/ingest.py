from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .memory import LocalMemory
from .models import Claim


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ0-9])")
CLAIM_CUES = (
    "show", "demonstrat", "result", "conclud", "suggest", "indicat",
    "improv", "reduc", "ensure", "crește", "arată", "rezult",
)


def read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF support requires: pip install -e '.[pdf]'") from exc
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if path.suffix.lower() not in {".txt", ".md"}:
        raise ValueError("Supported formats: .txt, .md, .pdf")
    return path.read_text(encoding="utf-8")


def extract_claims(text: str, source_id: str) -> list[Claim]:
    """Conservative extraction: preserves exact evidence and never invents metadata."""
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+.*$", " ", text)
    clean = re.sub(r"\s+", " ", text).strip()
    sentences = [s.strip() for s in SENTENCE_RE.split(clean) if 40 <= len(s.strip()) <= 600]
    selected = [s for s in sentences if any(cue in s.lower() for cue in CLAIM_CUES)]
    if not selected:
        selected = sentences[:20]
    claims = []
    for sentence in selected[:200]:
        tags = sorted({word.lower() for word in re.findall(r"\b[A-Za-zĂÂÎȘȚăâîșț-]{5,}\b", sentence)})[:8]
        claims.append(Claim(text=sentence, source_id=source_id, evidence=sentence, confidence=0.55, tags=tags))
    return claims


def ingest_file(memory: LocalMemory, raw_path: str | Path) -> dict:
    path = Path(raw_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if memory.has_source_hash(digest):
        return {"status": "duplicate", "source": path.name, "claims_added": 0}
    source_id = digest[:16]
    text = read_document(path)
    memory.add_source(source_id, path.stem, str(path), digest)
    count = memory.add_claims(extract_claims(text, source_id))
    return {"status": "ingested", "source_id": source_id, "source": path.name, "claims_added": count}
