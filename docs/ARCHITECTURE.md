# MigrationProof — Architecture

## What this system is

MigrationProof is an **evidence-grounded verification layer** for cloud migration
plans. It does not plan migrations or map infrastructure — those problems are
already solved by mature products (Google Cloud Migration Center, Device42,
Cloudamize, etc.). Its job is narrower and, we argue, still unowned: given a
*proposed* migration plan, it challenges that plan against heterogeneous
evidence and produces a deterministic, auditable **ALLOW / BLOCK** decision.

## High-level data flow

```
Raw artifacts (GCS)                    Benchmark ground truth
       │                                     ▲
       ▼                                     │
 Discovery Agent ──► candidate entities     │
 (Gemini/ADK)      candidate dependencies   │
       │                                     │
       ▼                                     │
 Evidence Agent ──► quoted snippets per     │
 (Gemini/ADK)      candidate dependency     │
       │                                     │
       ▼                                     │
   BigQuery (entities, dependencies,        │
   evidence, migration_waves)               │
       │                                     │
       ▼                                     │
 Deterministic Verification Engine          │
 (graph + rules; NO LLM)                    │
       │                                     │
       ▼                                     │
 ALLOW / BLOCK + reasons + confidence       │
 + blast radius ────────────────────────────┤ (benchmark compares to ground_truth)
       │
       ▼
 Analysis Agent (Gemini) — narrative only;
 structurally cannot change the decision
```

## Components

### Gemini + ADK agents (extraction, not decisions)

- **Discovery Agent** — reads raw artifacts (CSV/JSON/Markdown) and emits
  candidate entities + candidate dependencies as schema-validated JSON.
- **Evidence Agent** — for each candidate dependency, finds verbatim artifact
  excerpts supporting or contradicting it. A dependency with zero evidence is
  dropped before it ever reaches the verification engine.
- **Analysis Agent** — narrates an already-decided result. It receives only
  `decision`, `confidence`, `reasons`, and `blast_radius` and returns plain
  text. It structurally cannot alter the decision.
- **Orchestrator** (`app/agents/orchestrator.py`) — fetches a project's
  artifacts from GCS, runs Discovery then Evidence, and writes results to
  BigQuery.

### Deterministic verification engine (`app/verification/`)

The **only** component allowed to set ALLOW/BLOCK.

- `graph.py` — builds a dependency graph from verified BigQuery rows.
- `rules.py` — the rule set:
  - `cross_wave_dependency` — a dependency target scheduled for a later wave
    than the entity depending on it → **blocking**.
  - `contradictory_evidence` — evidence for the same dependency disagrees on
    whether it is active vs. decommissioned → **blocking**.
  - `low_confidence_dependency` — evidence too weak to trust → **advisory only**
    (flagged for human review, never auto-blocks by itself).
- `blast_radius.py` — transitive downstream dependents of each entity in the
  wave being verified.
- `confidence.py` — noisy-OR combination of evidence artifact types into a
  single 0–1 confidence score.

### Persistence (BigQuery)

Tables: `entities`, `dependencies`, `evidence`, `migration_waves`,
`ground_truth` (benchmark only), `verification_results`, `llm_call_log`
(cost/audit of every Gemini call).

### API (FastAPI)

- `POST /auth/login` — fixed-credential login, issues a signed bearer token.
- `POST /artifacts/upload/{project_id}` — upload raw artifacts to GCS.
- `POST /discovery/run/{project_id}` — run Discovery + Evidence agents.
- `GET /entities|/dependencies|/evidence|/waves` — inspection endpoints.
- `POST /verify` — run the deterministic engine + optional Analysis narrative.
- `GET /verify/{result_id}` — fetch a stored result.
- `GET /health` — liveness (note: `/healthz` is a reserved path on Cloud Run
  and is intercepted before reaching the container — use `/health`).

All routes except `/health` require the session bearer token.

## Why AI *and* deterministic logic

An LLM is good at extracting structured claims from messy, heterogeneous
artifacts. It is not a trustworthy arbiter of an infrastructure safety
decision — so it isn't one. Gemini/ADK produces *structured inputs*; a
deterministic graph/rules engine produces the *decision*. This makes the
safety call explainable, reproducible, unit-testable, and auditable, which is
exactly what a safety-adjacent product needs.

## Benchmark

`backend/benchmark/run_benchmark.py` runs the full pipeline (or the seeded
reference data, until a Gemini key is configured) against 8 controlled
synthetic scenarios and compares every decision to known `ground_truth`.
Results are written to `docs/BENCHMARK_RESULTS.md`.

Current numbers (against seeded reference data): 100% decision accuracy, 0%
unsafe-approval rate, 0% false-block rate, 100% contradiction-detection
accuracy across 8 scenarios.
