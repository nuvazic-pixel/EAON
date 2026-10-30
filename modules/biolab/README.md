# EAON BioLab M0 — Foundation

Local-first, synthetic-only biological time-series validation. No clinical use.

Run from the EAON root:

```bash
python scripts/run_module.py biolab smoke --count 100
```

Tests from this module:

```bash
PYTHONPATH=src python -m pytest tests -q
```

The CLI loads the fixed experiment YAML subset with a dependency-free strict
loader. Duplicate keys and invalid policies are rejected; this is not a general YAML parser.
Invalid JSONL records are quarantined in returned error records, not silently discarded.
