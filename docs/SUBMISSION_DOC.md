# MigrationProof — Evidence-Grounded Verification for Cloud Migrations

## 1. Project Description

MigrationProof is a verification layer for cloud migration plans. Before a team cuts over a batch of services ("a wave") to new infrastructure, MigrationProof checks whether the plan is actually safe and returns a hard **ALLOW / BLOCK** decision backed by cited evidence — not a guess from a chatbot.

The product is intentionally **not** a migration planner or a dependency-mapping tool — those already exist and are mature (Google Cloud Migration Center, Device42, Cloudamize, Flexera, Turbonomic, etc.). MigrationProof's job is narrower and unclaimed: independently challenge an already-proposed plan and demand proof before approving it.

The system works as follows:

- Raw infrastructure artifacts (VM inventories, DNS records, application configs, architecture docs, network connection logs) plus a proposed migration wave plan are uploaded.
- A **Discovery Agent** (Gemini, orchestrated via Google ADK) reads the raw artifacts and proposes candidate entities (services, databases, VMs, DNS records, external APIs) and candidate dependencies between them.
- An **Evidence Agent** (Gemini) finds a verbatim quoted excerpt from a real artifact supporting (or contradicting) each candidate dependency. Any dependency with zero supporting evidence is dropped immediately — it can never reach the decision layer.
- A **deterministic Verification Engine** (plain Python, graph + rule logic, **no AI**) is the only component allowed to make the ALLOW/BLOCK decision. It checks: cross-wave dependency violations (a service depends on something scheduled for a later wave), contradictory evidence (one artifact says a dependency is active, another says it was decommissioned), and low-confidence dependencies (flagged for human review, not auto-blocked).
- The engine also computes a **blast radius** — every downstream service that would be affected if a disrupted entity fails — and a confidence score.
- An **Analysis Agent** (Gemini) writes a plain-English narrative explaining the decision that was **already made**. It cannot change the verdict; it receives only the decision, reasons, confidence, and blast radius as read-only input.

**Why AI + deterministic logic together:** an LLM is excellent at reading messy, heterogeneous artifacts and extracting structured claims, but it is not a trustworthy arbiter of an infrastructure safety decision. By making the actual ALLOW/BLOCK call a deterministic, unit-tested function of structured data, the result is explainable, reproducible, and auditable — which matters enormously for a safety-adjacent product.

We validated this design with a benchmark: 8 controlled synthetic scenarios (RetailCo, a fictional e-commerce environment) with known ground truth, covering safe migrations, cross-wave violations, contradictory evidence, and low-confidence dependencies. Result: **100% decision accuracy, 0% unsafe-approval rate** (the most dangerous failure class for a safety tool), **0% false-block rate**.

**Tech stack:** Python + FastAPI backend, React + TypeScript + Vite frontend, Gemini 2.5 Flash via Vertex AI (Google ADK-style multi-agent orchestration: Discovery → Evidence → Verification → Analysis), BigQuery for structured entity/dependency/evidence/results storage, Google Cloud Storage for raw artifacts, Secret Manager for credentials, all deployed on Cloud Run.

## 2. Project Use Case

**Primary use case:** A platform/DevOps team is planning a multi-wave migration (e.g. AWS to GCP, on-prem to cloud, or a re-architecture). Before executing Wave 1, an engineer opens MigrationProof, uploads the relevant infrastructure artifacts and the proposed wave plan (or selects an already-analyzed project), and clicks "Verify Wave 1".

**Example — the flagship scenario:**

A `checkout-api` service is scheduled for Wave 1. It depends on `mysql-prod`, which is scheduled for Wave 3. If this migration proceeds as planned, `checkout-api` would go live in a new environment with no working database connection, taking down checkout, orders, and payments.

MigrationProof catches this automatically:

| Field | Value |
|---|---|
| Result | **BLOCKED** |
| Reason | `checkout-api` (Wave 1) depends on `mysql-prod`, which is scheduled for Wave 3 |
| Confidence | 90% |
| Blast radius | checkout-api, frontend, order-service, payment-service, redis, kafka, load-balancer, external-payment-api |
| Explanation | Gemini-generated plain-English summary with a concrete recommendation (move `mysql-prod` earlier, or delay `checkout-api`) |

**Secondary use cases demonstrated by the 8 pre-loaded scenarios:**

- Safe migration correctly ALLOWed with no false positives.
- Stale/contradictory evidence detection (e.g. a DNS record marked decommissioned but still referenced in an active config).
- Weak/low-confidence dependencies flagged for human review without being wrongly auto-blocked (avoids "cry wolf" fatigue).
- Dependencies on entities outside the migration's scope (external APIs) correctly treated as non-blocking.

**Target users:** platform engineering / SRE / cloud migration teams who need an independent, evidence-backed sign-off step before executing a cutover, rather than trusting a spreadsheet or a single engineer's memory of "I think that's fine."

**Longer-term product vision:** continuous verification, not just pre-migration — MigrationProof could run PLAN → VERIFY → MIGRATE → VERIFY → DRIFT DETECTION cycles, catching not just planning mistakes but also cases where the live environment has drifted from the approved, verified plan.

## 3. Architecture Diagram

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

**Key design principle shown in the diagram:** Gemini (Discovery, Evidence, Analysis agents) only ever produces structured, cited input or a post-hoc explanation. The Verification Engine — pure Python, no AI, fully unit tested — is the only component that outputs the ALLOW/BLOCK decision.

**Deployed services** (Cloud Run, project `migrationguard-sv`, `us-central1`):

- `migrationproof-backend` — FastAPI + Gemini agents + verification engine
- `migrationproof-frontend` — React SPA, served via nginx

**Data stores:** BigQuery dataset `migrationproof` (7 tables: `entities`, `dependencies`, `evidence`, `migration_waves`, `ground_truth`, `verification_results`, `llm_call_log`), 2 GCS buckets (artifacts, synthetic-data).

---

**Developed by:** Supriti Vats
Email: supritivats123@gmail.com
LinkedIn: https://www.linkedin.com/in/supriti-vats/
Portfolio: https://supriti-vats-portfolio.netlify.app/
GitHub: https://github.com/SupritiVats
