"""EAON knowledge ingestion pipeline."""

from .openalex import OpenAlexClient, OpenAlexWork
from .claim_extractor import ClaimExtractor, ExtractedClaim
from .knowledge_store import KnowledgeStore

__all__ = ["OpenAlexClient", "OpenAlexWork", "ClaimExtractor", "ExtractedClaim", "KnowledgeStore"]
