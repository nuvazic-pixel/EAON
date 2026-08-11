from ingestion.claim_extractor import ClaimExtractor
from ingestion.knowledge_store import KnowledgeStore
from ingestion.openalex import OpenAlexClient, reconstruct_abstract

def test_reconstruct_abstract_orders_tokens():
    inverted = {"World": [1], "Hello": [0], "again": [2]}
    assert reconstruct_abstract(inverted) == "Hello World again"

def test_normalize_extract_and_store(tmp_path):
    payload = {
        "id": "https://openalex.org/W123",
        "display_name": "Microglia and immune signalling",
        "publication_year": 2010,
        "publication_date": "2010-04-01",
        "doi": "https://doi.org/10.1234/example",
        "abstract_inverted_index": {
            "Our": [0], "results": [1], "show": [2], "that": [3],
            "microglial": [4], "activation": [5], "increases": [6],
            "inflammatory": [7], "signalling.": [8]
        },
        "cited_by_count": 42,
        "referenced_works": ["https://openalex.org/W99"],
        "topics": [{"display_name": "Neuroimmunology"}],
        "primary_location": {"source": {"display_name": "Example Journal"}},
        "open_access": {"is_oa": True},
    }
    work = OpenAlexClient.normalize_work(payload)
    claims = ClaimExtractor().extract(work)
    assert work.abstract.startswith("Our results show")
    assert len(claims) == 1
    assert "microglial activation" in claims[0].text
    db_path = tmp_path / "knowledge.db"
    with KnowledgeStore(db_path) as store:
        assert store.ingest(work, claims) == 1
        assert store.stats() == {"works": 1, "claims": 1}
