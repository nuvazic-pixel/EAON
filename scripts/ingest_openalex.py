#!/usr/bin/env python3
"""Ingest a bounded OpenAlex batch into EAON's local knowledge store."""
from __future__ import annotations
import argparse
from ingestion import ClaimExtractor, KnowledgeStore, OpenAlexClient

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="OpenAlex text search query")
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--max-works", type=int, default=100)
    parser.add_argument("--db", default="data/eaon_knowledge.db")
    return parser

def main() -> int:
    args = build_parser().parse_args()
    client = OpenAlexClient()
    extractor = ClaimExtractor()
    ingested_works = ingested_claims = 0
    with KnowledgeStore(args.db) as store:
        for work in client.iter_works(args.query, from_year=args.from_year, to_year=args.to_year, max_works=args.max_works):
            claims = extractor.extract(work)
            store.ingest(work, claims)
            ingested_works += 1
            ingested_claims += len(claims)
            print(f"[{ingested_works}] {work.publication_year or '-'} | {len(claims)} claims | {work.title[:90]}")
        stats = store.stats()
    print(f"Ingestion complete: batch_works={ingested_works}, batch_claims={ingested_claims}, db_works={stats['works']}, db_claims={stats['claims']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
