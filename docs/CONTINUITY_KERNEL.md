# Continuity kernel v0.1

`eaon_kernel` keeps explicit project state in a local SQLite event journal.
It uses the Python standard library and contains no model, tool executor or
automatic migration of existing stores. The other EAON modules remain separate
entrypoints; the kernel does not yet coordinate the complete voice/UI workflow.

## Start and recover

Run from the repository root. Put the global `--db` argument before the command.
Choose a new path for `init`; it refuses to overwrite an existing file. Every
other command requires an existing database and fails if it is missing.

```sh
python -m eaon_kernel --db data/continuity.db init
python -m eaon_kernel --db data/continuity.db project demo "Continuity demo" --max-tasks 8 --owner local
python -m eaon_kernel --db data/continuity.db goal demo g1 "Keep the next session reproducible"
python -m eaon_kernel --db data/continuity.db remember demo approach "Use local state" --status hypothesis
python -m eaon_kernel --db data/continuity.db unknown demo latency "Hardware latency has not been measured"
python -m eaon_kernel --db data/continuity.db task demo t1 "Measure hardware latency"
python -m eaon_kernel --db data/continuity.db recover demo
```

The equivalent launcher is `python scripts/run_module.py kernel --db ...`.
With that launcher, relative paths resolve from the repository root. Commands
print JSON; rejected input or integrity failures return a nonzero exit code.

`recover` reconstructs the goal, task history, memories and next pending task.
There is one active goal per project. The pending-task limit defaults to eight
and must be between one and 100. Complete pending tasks before closing the goal:

```sh
python -m eaon_kernel --db data/continuity.db task demo t1 --complete
python -m eaon_kernel --db data/continuity.db goal demo --close
```

Goal and task identifiers cannot be reused in that project. Recording a task
does not execute it.

## Memory and sources

Memory has an explicit epistemic state: `hypothesis`, `confirmed` or `unknown`.
`remember` defaults to `hypothesis`. Confirmation requires at least one captured
UTF-8 source file; repeat `--source-file` to attach several:

```sh
python -m eaon_kernel --db data/continuity.db remember demo approach "Use local state" --status confirmed --source-file evidence/decision.txt --expected-revision 1
```

Create that source file separately from the command, containing the evidence
you intend to preserve. Its text, URI and SHA-256 are captured in the journal.
The digest verifies the captured text's identity. It does not establish the
statement's truth, entailment, author or current contents of the original file.
Confirmation is an explicit caller decision with evidence attached.

New keys begin at revision one. Updating or revoking a key requires its current
revision, obtained from `recover`, so stale writers cannot silently replace it.

```sh
python -m eaon_kernel --db data/continuity.db revoke demo approach "Decision superseded" --expected-revision 2
```

Revocation is another event and increments the revision. Historical records
remain inspectable with `recover`; active context and provider snapshots exclude
revoked memories. `--kind profile|episodic|task|skill|evidence` stores a namespaced
key such as `evidence:decision`. To revoke such a key with the CLI, pass the full
namespaced key. A stored skill never activates or gains tool authority.

## Integrity and checkpoints

Reads and writes replay the hash chain, canonical payloads, policy binding and
valid state transitions. Writes validate and append inside a SQLite transaction.
Journal head/count metadata detects partial edits or truncation when the
metadata is retained. An invalid store is rejected before returning context.

```sh
python -m eaon_kernel --db data/continuity.db checkpoint demo
python -m eaon_kernel --db data/continuity.db verify
python -m eaon_kernel --db data/continuity.db verify --expected-head HEAD_SAVED_OUTSIDE_THE_DATABASE
```

`checkpoint` returns the journal head and reconstructed project-state hash.
Keep a trusted expected head outside the database to detect replacement with
an older, otherwise internally consistent database. Local hashes and metadata
alone cannot detect coordinated rewriting or rollback of the entire file.
After legitimate new events, save the new trusted head before using it as the
next exact comparison. These hashes are not signatures or external attestations.

## Provider routing and evidence selection

The Python API in `eaon_kernel.memory` registers separate providers for
`profile`, `episodic`, `task`, `skill` and `evidence`. `query_for_intent` maps
explicit intents deterministically:

| Intent | Provider kind |
|---|---|
| `profile_lookup` | `profile` |
| `past_episode` | `episodic` |
| `project_state` | `task` |
| `validated_procedure` | `skill` |
| `document_question` | `evidence` |

This selects memory, independently of model routing. Callers supply a
`MemoryScope` with owner, project and privacy class, plus collection when
needed. Register remote providers with `locality="remote"`; a `local` scope
rejects them before retrieval. The kernel's owner field is a local scoping
contract, not an operating-system identity or authentication service.
SQLite stores captured source text in plaintext. Protect the database with
appropriate operating-system file permissions; owner filters do not encrypt it
or replace authentication when exposing a service.

Candidates are filtered by owner, collection, revocation and expiry before
ranking. Conflicting content for one provider/source identity is rejected.
Selection prioritizes required source IDs within an explicit **character**
budget (default 12,000), then ranks other eligible fragments deterministically.
Oversized fragments are omitted, not silently truncated.

Missing required sources produce `unknown_required_fact`; declared contradictions
produce `contested`. `retrieved` only means eligible fragments were selected.
The evidence-confidence field is a coverage/document-diversity heuristic, not a
calibrated truth probability. Context remains `candidate_only` and grants no
permission to run a tool or append confirmed memory.

For local evidence, save source-backed memories with `--kind evidence`, then:

```sh
python -m eaon_kernel --db data/continuity.db context demo "local state" --budget-chars 6000
```

## Genesis and Synapse boundaries

`GenesisEvidenceProvider(path, owner_id="local", expected_head=None)` is a
read-only Python bridge for one explicitly selected legacy Genesis JSONL file.
It verifies the original record schema/hash chain before returning matching
source snapshots. It does not migrate or confirm records. An external expected
head is necessary to detect replacement with another consistent legacy journal;
a source digest alone does not authenticate its author.

The Synapse bridge requires the new
[evidence API change](https://github.com/nuvazic-pixel/rage-against-the-machine/pull/1).
The interoperability CI pins Synapse commit
`86c228de234a8da38b69824e17e8862d3912f4b9`.
Create the EAON project with `--owner` equal to the authenticated Synapse user
UUID. Supply an owned collection UUID and place the account token in the
`SYNAPSE_TOKEN` environment variable; the client does not load `.env` files.

```sh
python -m eaon_kernel --db data/synapse-context.db context project-id "source question" --synapse-url http://127.0.0.1:8000 --collection-id OWNED_COLLECTION_UUID
```

Use an already initialized database/project in that command. The bridge calls
only `GET /chat/evidence`, checks query/owner/collection, freshness, schema and
fragment hashes, and marks fragments as expiring candidates. Synapse checks
active-account authentication, collection ownership and retrieval budget, and
bypasses its search-result cache. Retrieval does not append to the kernel.
The existing bearer token is an account credential; it is not a separately
scoped read-only token. The client defaults to loopback; the Python API permits
remote HTTPS only with explicit opt-in and a compatible privacy scope.

## Reproduction

```sh
python scripts/demo_continuity.py
python scripts/verify_workspace.py --report-dir verification-results
python scripts/probe_synapse_contract.py --synapse-root PATH_TO_PINNED_SYNAPSE_CHECKOUT
```

The demo creates synthetic state in a temporary directory and uses fresh
processes to write, recover and verify it. The cross-repository probe uses the
actual HTTP schema and signed synthetic JWTs with fake infrastructure. It needs
Synapse's `requirements-contract-tests.txt`; the isolated workspace verifier
uses EAON's `requirements-verify.txt`. Synapse separately exercises native
PostgreSQL/pgvector and Redis in disposable CI services, with deterministic
embedding/reranker fixtures. These checks do not establish model quality,
hardware latency or production deployment behavior.
