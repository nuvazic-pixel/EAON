# EAON BioLab M0 — Foundation

Local-first, synthetic-only biological time-series validation. No clinical use.

Run from the EAON root after launcher integration:

```bash
python scripts/run_module.py biolab smoke --count 100
```

Tests from this module:

```bash
PYTHONPATH=src python -m pytest tests -q
```

The YAML file is the experiment specification. M0 CLI mirrors its initial values
without introducing a YAML dependency; config loading is a later integration task.
Invalid JSONL records are quarantined in returned error records, not silently discarded.
