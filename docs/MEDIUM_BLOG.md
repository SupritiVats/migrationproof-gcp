# MigrationProof: Why I Built an Evidence-First Safety Layer for Cloud Migrations

**Description:** A walkthrough of MigrationProof, a Patchamomma 2026 project that independently verifies cloud migration plans using Gemini for extraction and a deterministic rules engine for the final ALLOW/BLOCK decision.

---

## The Problem: Migrations Fail in Predictable Ways

Every enterprise cloud migration plan looks reasonable in a spreadsheet. The schedule has waves, the dependency tracker is color-coded, and the cutover runbook is approved. Then Wave 1 executes and a service goes down because the database it relies on is not scheduled to move until Wave 3.

This is not a rare edge case. It is the most common failure pattern in migration projects: a service is scheduled to move earlier than something it actually depends on, and nobody catches the mismatch before cutover.

The existing tooling landscape is mature in the wrong places. Google Cloud Migration Center, Device42, Cloudamize, Flexera, Turbonomic, and Dynatrace are excellent at discovery, dependency mapping, and wave planning. What they do not do well is act as an independent challenger. They will happily let you create a plan in which `checkout-api` moves in Wave 1 and `mysql-prod` moves in Wave 3, because planning tools assume the human is the final verifier.

I built MigrationProof to close that gap: an evidence-grounded verification layer that reads the actual artifacts, extracts the actual dependencies, and produces a hard ALLOW or BLOCK decision before the migration executes.

---

## What MigrationProof Does

MigrationProof asks one question: **"Is the proposed next wave actually safe to execute?"**

The answer is not a recommendation, a confidence band, or an LLM opinion. It is a binary decision, supported by cited evidence:

```
BLOCK

checkout-api (Wave 1) depends on mysql-prod (Wave 3).

Evidence:
- config.php: DB_HOST=mysql-prod.internal
- DNS record: mysql-prod.internal -> 10.20.0.14
- architecture.md: "checkout-api reads/writes to mysql-prod"

Predicted blast radius:
- checkout-api
- order-service
- payment-service

Confidence: 90%
```

The key constraint is that the final safety decision is made by deterministic code, not by an LLM. Gemini is used to extract structure and evidence from messy artifacts. The decision itself is a graph-based rule check on that structured data.

---

## The Use Case

The primary user is a platform or SRE team preparing a multi-wave migration. Before executing a wave, the engineer uploads the infrastructure artifacts and the proposed migration plan, or loads a pre-analyzed project, and verifies the wave.

The flagship scenario, which drives home why this matters, is a fictional RetailCo e-commerce environment:

- `checkout-api` is in Wave 1.
- `mysql-prod`, which `checkout-api` depends on, is in Wave 3.
- If Wave 1 executes as planned, `checkout-api` has no working database connection.

MigrationProof catches this automatically and returns BLOCK with a confidence score and a blast radius that includes every downstream service affected.

The secondary use cases cover the other common ways migration plans fail: contradictory evidence, stale references, low-confidence dependencies that should be reviewed by a human, and external dependencies outside the migration scope.

---

## How It Solves the Problem

The design principle is simple: AI reads, deterministic code decides.

### 1. Discovery Agent

A Gemini-based Discovery Agent reads the uploaded artifacts (VM inventories, DNS records, application configs, architecture documents, network connection logs) and proposes candidate entities and dependencies. The output is structured JSON, not free text.

### 2. Evidence Agent

For every candidate dependency, an Evidence Agent searches the original artifacts for a verbatim quoted excerpt that supports or contradicts it. If no evidence exists, the dependency is dropped. It can never reach the decision layer.

### 3. Deterministic Verification Engine

This is a pure Python graph and rule engine. It is the only component allowed to produce the ALLOW/BLOCK decision. It checks:

- Cross-wave dependency violations: a service in Wave 1 depends on a service in a later wave.
- Contradictory evidence: one artifact says a dependency is active, another says it is decommissioned.
- Low-confidence dependencies: flagged for human review, not auto-blocked.
- Blast radius: every downstream service that would be affected by a failure.

### 4. Analysis Agent

After the deterministic decision is made, a Gemini Analysis Agent writes a human-readable narrative. It receives the decision, reasons, confidence, and blast radius as read-only inputs. It cannot change the verdict.

---

## Architecture

```
                              USER (browser)
                                    |
                         +----------------------+
                         |   React Frontend      |   (Cloud Run)
                         |   login / upload /     |
                         |   verify UI             |
                         +----------+-----------+
                                    | REST + Bearer token
                         +----------------------+
                         |   FastAPI Backend      |   (Cloud Run)
                         +----------+-----------+
                    +----------------+----------------+
                    |                |                 |
          +-------------------+  +-----------+  +----------------+
          |  Cloud Storage     |  | BigQuery  |  | Secret Manager |
          |  raw artifacts     |  | entities /|  | passwords /    |
          +---------+---------+  | deps /    |  | API keys       |
                    |             | evidence  |  +----------------+
                    v             +-----+-----+
          +-----------------------+     |
          | Gemini + ADK Agents    |     |
          |  Discovery Agent  ------------+  writes candidate entities + deps
          |  Evidence Agent   ------------+  writes cited evidence per dependency
          |  Analysis Agent    (writes narrative AFTER decision is made)
          +-----------------------+
                                    |
                                    v
                     +--------------------------+
                     | Deterministic             |
                     | Verification Engine       |
                     | (graph + rules, NO AI)     |
                     +-------------+--------------+
                                    v
                       ALLOW / BLOCK + reasons
                       + confidence + blast radius
```

The diagram shows the critical split: the AI agents produce structured, cited input and a post-hoc explanation. The Verification Engine, written in pure Python and fully unit tested, owns the safety decision.

---

## Implementation Steps

The build followed a strict order: data and verification first, UI and deployment last. Skipping ahead would have produced a nice dashboard with nothing trustworthy behind it.

### Phase 1: Synthetic Environment and Ground Truth

I built a fictional RetailCo e-commerce environment and generated eight controlled scenarios with known correct answers. Each scenario includes:

- `dns_records.csv`
- `service_catalog.csv`
- `architecture.md`
- `migration_plan.json`
- `application_config.json`
- `vm_inventory.csv`
- `reference_data.json` (answer key, never shown to the agents)

The scenarios cover ALLOW, BLOCK, contradictory evidence, stale references, low-confidence dependencies, and cross-wave conflicts.

### Phase 2: BigQuery Schema

I created a `migrationproof` dataset in BigQuery with seven tables:

- `entities`
- `dependencies`
- `evidence`
- `migration_waves`
- `ground_truth`
- `verification_results`
- `llm_call_log`

This is the single source of truth for the verification engine. Every claim, dependency, and evidence record is stored and queryable.

### Phase 3: Deterministic Verification Engine

This was built before any AI agent. It needed to work correctly on known inputs before I trusted it with LLM-extracted data. It includes:

- Graph construction from entities and dependencies
- Cross-wave dependency rules
- Contradiction and stale-reference detection
- Confidence scoring
- Blast-radius computation using reverse dependency traversal

The benchmark goal was 100% decision accuracy, 0% unsafe-approval rate, and 0% false-block rate against the eight scenarios.

### Phase 4: Gemini Agents

With the engine in place, I added the Gemini agents via the Google ADK-style orchestrator:

- Discovery Agent: extracts structured entities and dependencies from heterogeneous artifacts.
- Evidence Agent: finds supporting or contradicting evidence for each candidate dependency.
- Analysis Agent: writes a plain-English explanation of the deterministic result.

All prompts require structured output and every LLM call is logged to BigQuery for auditability and cost tracking.

### Phase 5: FastAPI Backend

The backend exposes:

- `GET /health`
- `POST /auth/login`
- Artifact upload, list, and delete endpoints
- Discovery and inspection endpoints
- Verification endpoint returning `result_id`, `decision`, `reasons`, `confidence`, `blast_radius`, and a `narrative`

It runs on Cloud Run and reads credentials from Google Secret Manager in production.

### Phase 6: React Frontend

The frontend is a React + TypeScript + Vite SPA. It includes:

- Login screen
- Project workflow: load scenario, upload artifacts, run discovery, view entities, inspect waves, verify
- Wave timeline
- Result page with ALLOW/BLOCK banner, confidence, reasons, blast radius, and narrative
- About page with architecture pipeline, usage guide, and scenario table

### Phase 7: Deployment

Both backend and frontend are deployed to Google Cloud Run in the `migrationguard-sv` project. The data layer is BigQuery and Cloud Storage, with Secret Manager for credentials.

---

## Validation: The Benchmark

I tested the full system against all eight RetailCo scenarios. The verification engine produced:

- 100% decision accuracy
- 0% unsafe-approval rate
- 0% false-block rate

This matters because the most dangerous failure class for a safety tool is approving an unsafe plan. MigrationProof never did.

---

## Key Takeaway

LLMs are excellent readers of messy infrastructure artifacts, but they should not be the final arbiter of an infrastructure safety decision. By separating evidence extraction from the safety decision, MigrationProof becomes explainable, reproducible, and auditable. That is the difference between a chatbot that says "looks risky" and a system that can be benchmarked, trusted, and deployed before a cutover.

---

**Live demo:** https://migrationproof-frontend-509319730686.us-central1.run.app  
**GitHub:** https://github.com/SupritiVats/migrationproof-gcp  
**Developed by:** Supriti Vats

---

*Built for Patchamomma 2026.*
