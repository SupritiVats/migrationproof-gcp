# MigrationProof — Patchamomma 2026 Submission

> **An evidence-grounded verification layer that challenges a proposed cloud migration plan and determines whether it is actually safe to execute — before you cut over.**

This README is the **single source of truth** for building, testing, and deploying MigrationProof. It is written to be handed directly to an AI coding agent (Devin, Claude, etc.) as an implementation specification, and also to be read by a human judge/reviewer.

---

## 0. Instructions for the coding agent (read first)

> **You are the primary implementation engineer for MigrationProof, a Patchamomma 2026 submission.**
>
> - Do **not** redesign the product, change the architecture, substitute technologies, or simplify core functionality without explicit approval from the project owner.
> - Follow this specification **sequentially**, phase by phase (see [Section 8 — Build Order](#8-build-order-follow-sequentially)). Do not skip ahead to UI or deployment before earlier phases are functionally complete and tested.
> - If a requirement is ambiguous or underspecified, **STOP and report the ambiguity** instead of inventing a solution.
> - The final system must be:
>   - Runnable **locally** with a documented set of commands.
>   - Deployable to **Google Cloud Run** (both backend and frontend).
> - Every major feature must be **testable**, and a feature is not "done" until it has been implemented **and** verified against its acceptance criteria (see "Definition of Done" in each phase).
> - Do not claim a feature is complete in commit messages, PRs, or status updates until it passes its Definition of Done.
> - Keep secrets out of source control. Use `.env` files (git-ignored) locally and **Google Secret Manager** in production.
> - Prefer deterministic, testable logic for anything that constitutes a **safety decision** (ALLOW/BLOCK). Gemini/ADK is used for **extraction and reasoning support**, never as the final arbiter of a safety decision.
> - Keep cloud spend minimal. Use small/cheap Gemini models for extraction, cache results, and avoid unnecessary reprocessing (see [Section 15 — Cost Controls](#15-cost-controls)).

---

## 1. What are we building?

A company says: *"Tomorrow we're migrating these 5 services."*

They give MigrationProof:

```
Infrastructure data
├── VM inventory
├── DNS records
├── application configs
├── network information
├── architecture documents
└── proposed migration plan (waves)
```

The user asks: **"Can I safely execute Wave 1?"**

MigrationProof responds with a decision, **backed by evidence**:

```
🔴 BLOCK

checkout-api (Wave 1) depends on mysql-prod (Wave 3).

Evidence:
✓ config.php:  DB_HOST=mysql-prod.internal
✓ DNS record:  mysql-prod.internal → 10.20.0.14
✓ architecture.md: "checkout-api reads/writes to mysql-prod"

Predicted blast radius:
- checkout-api
- order-service
- payment-service

Confidence: 97%

Recommendation: Move mysql-prod to Wave 1, or remove the dependency.
```

### What this is NOT

Cloud discovery, dependency mapping, and migration-wave planning already exist as mature products (Google Cloud Migration Center; AWS's ecosystem of Device42, Cloudamize, Flexera, Turbonomic, Dynatrace, etc.). We are **not** competing on discovery or planning.

| We are **not** building | We **are** building |
|---|---|
| An AI migration planner | A verification & challenge layer for migration decisions |
| A dependency-mapping tool | A system that demands **evidence** before approving a cutover |
| An AWS → GCP migration assistant | A benchmarked, evidence-backed ALLOW/BLOCK decision engine |

**Positioning:** *Migration Center tells you what you have and helps you plan. MigrationProof asks: "Show me the evidence that proves this plan is safe."*

---

## 2. Why now / is there a market

- Cloud migration guidance already emphasizes discovery, dependency mapping, migration waves, and risk assessment — this is a known, real, ongoing pain point for enterprises migrating infrastructure.
- Agentic AI in cloud engineering is trending, but the emerging consensus is that autonomous systems need **verification, bounded execution, and evidence** — not just free-form reasoning. That is exactly our design philosophy: *AI reasons, evidence supports, deterministic logic verifies.*
- **Competitive honesty:** Discovery/dependency-mapping tools already exist (Google Migration Center, Device42, Cloudamize, Flexera, Turbonomic, Dynatrace, etc.). Our differentiation is narrow and specific: **independently challenging a proposed migration plan against heterogeneous evidence, and producing a benchmarked, evidence-backed safety decision** — not the discovery/planning step itself.
- Novelty is intentionally rated moderate (not "we invented something new" — we're filling a specific, demonstrable gap with rigor: evidence grounding + deterministic verification + a benchmark against known ground truth).

---

## 3. Architecture

```
                        USER
                          │
                          ▼
                 ┌─────────────────┐
                 │  Web Dashboard   │  (React, basic-auth protected)
                 └────────┬────────┘
                          │ upload artifacts / view results
                          ▼
                 ┌─────────────────┐
                 │  FastAPI Backend │  (Cloud Run)
                 └────────┬────────┘
                          │
             ┌────────────┼─────────────┐
             ▼            ▼             ▼
     ┌───────────────┐ ┌─────────┐ ┌──────────────┐
     │ Cloud Storage  │ │BigQuery │ │Secret Manager│
     │ raw artifacts  │ │  data   │ │  API keys    │
     └───────┬────────┘ └────┬────┘ └──────────────┘
             │               │
             ▼               │
   ┌───────────────────────┐ │
   │   Gemini + ADK Agents  │ │
   │                        │ │
   │  Orchestrator          │ │
   │   ├─ Discovery Agent   │ │
   │   ├─ Evidence Agent    │ │
   │   └─ Analysis Agent    │ │
   └───────────┬────────────┘ │
               │  structured entities/deps/evidence
               └──────────────┼──────────┐
                               ▼          ▼
                      ┌─────────────────────────┐
                      │  BigQuery (source of     │
                      │  truth for entities,     │
                      │  dependencies, evidence,│
                      │  waves, ground truth)    │
                      └────────────┬─────────────┘
                                   ▼
                      ┌─────────────────────────┐
                      │ Deterministic            │
                      │ Verification Engine      │
                      │ (graph + rules, Python)  │
                      └────────────┬─────────────┘
                                   ▼
                          ┌────────────────┐
                          │ ALLOW / BLOCK  │
                          └───────┬────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │ Evidence + Blast Radius │
                     │ + Confidence output     │
                     └─────────────────────────┘
```

### Why both AI *and* deterministic logic?

We do not trust an LLM to make the final safety call. Gemini/ADK is excellent at reading messy, heterogeneous artifacts (configs, DNS zone files, architecture docs) and extracting **structured claims** ("checkout-api appears to connect to mysql-prod"). But the final question — *"does Wave 1 violate a known dependency?"* — is answered by a **deterministic graph/rules engine** operating on structured data in BigQuery. This makes the safety decision explainable, reproducible, and testable, which matters enormously for an infra-safety product.

```
Gemini/ADK  →  "checkout-api → mysql-prod" (structured claim + evidence)
                       │
                       ▼
        Deterministic verification engine
                       │
        mysql-prod = Wave 3, checkout-api = Wave 1
                       │
                       ▼
                  ❌ BLOCK (rule: cross-wave dependency)
```

---

## 4. Agent design (Gemini + ADK)

Do **not** over-engineer with 5+ autonomous agents. Use a small, supervised set:

```
                 Orchestrator (ADK)
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
  Discovery Agent  Evidence Agent   Analysis Agent
   (extracts        (extracts       (drafts blast-radius
   entities from     supporting      hypothesis + narrative
   inventories/      quotes/refs     explanation; NOT the
   configs/DNS)      per claim)      final decision)
        │               │                │
        └───────────────┼────────────────┘
                         ▼
          Deterministic Verification Engine
                         │
                         ▼
                  ALLOW / BLOCK
```

Agent responsibilities:

| Agent | Input | Output | Notes |
|---|---|---|---|
| **Discovery Agent** | Raw artifacts (CSV/JSON/Markdown) from GCS | Candidate entities (services, DBs, VMs) + candidate dependencies | Structured JSON only, schema-validated |
| **Evidence Agent** | Candidate dependency + source artifacts | Evidence records: artifact ref, quoted snippet, evidence type | Every claim must cite ≥1 evidence source or is discarded |
| **Analysis Agent** | Verified dependency graph + migration plan | Natural-language blast-radius narrative, human-readable explanation | Advisory only — does not set ALLOW/BLOCK |
| **Verification Engine** (deterministic, not an LLM agent) | Structured entities/dependencies/evidence + migration plan from BigQuery | ALLOW/BLOCK + reasons + confidence | The only component allowed to set the final decision |

All agent prompts must require structured (JSON-schema-validated) output. Store the prompts under `backend/agents/prompts/`. Log every LLM call's input/output to BigQuery (`llm_call_log` table) for auditability and cost tracking.

---

## 5. Confirmed technical decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Backend | Python + FastAPI |
| 2 | Frontend | React + Vite |
| 3 | AI framework | Google ADK + Gemini API |
| 4 | Database | BigQuery |
| 5 | File/artifact storage | Google Cloud Storage |
| 6 | Deployment | Cloud Run — backend **and** frontend, separate services |
| 7 | Authentication | No user accounts/OAuth for MVP. Dashboard is protected by a **single fixed username/password** (HTTP Basic Auth or a simple login gate) — good enough for a public demo URL without leaving it wide open |
| 8 | Data | Fully synthetic enterprise migration environment with known ground truth (+ optionally a real BigQuery public dataset, clearly labeled as supplementary, not load-bearing for the core demo) |

---

## 6. Repository structure

```
migrationproof-gcp/
├── README.md                          # this file
├── AGENTS.md                          # notes/learnings for coding agents (create as you go)
├── .env.example
├── .gitignore
├── infra/
│   ├── terraform/                     # optional: IaC for GCP resources
│   ├── bigquery/
│   │   └── schema/                    # DDL / JSON schema per table
│   └── cloudrun/
│       ├── backend-service.yaml
│       └── frontend-service.yaml
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── api/                       # routers: artifacts, verify, waves, evidence
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── discovery_agent.py
│   │   │   ├── evidence_agent.py
│   │   │   ├── analysis_agent.py
│   │   │   └── prompts/
│   │   ├── verification/
│   │   │   ├── graph.py               # dependency graph model
│   │   │   ├── rules.py               # deterministic rule set
│   │   │   ├── blast_radius.py
│   │   │   └── confidence.py
│   │   ├── storage/                   # GCS + BigQuery clients
│   │   ├── models/                    # pydantic schemas
│   │   ├── auth/                      # fixed-credential basic auth
│   │   └── config.py
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── benchmark/
│   │   ├── scenarios/                 # generated synthetic scenarios + ground truth
│   │   ├── run_benchmark.py
│   │   └── metrics.py
│   ├── scripts/
│   │   └── generate_synthetic_data.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/                     # Upload, Dashboard, WaveReview, VerificationResult
│   │   ├── components/
│   │   ├── api/                       # fetch client for backend
│   │   └── auth/                      # login gate
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
└── docs/
    ├── ARCHITECTURE.md
    ├── BENCHMARK_RESULTS.md
    └── DEMO_SCRIPT.md
```

---

## 7. Local prerequisites (Linux)

Install once, in this order. Verify each with the given command.

```bash
# 1. System packages
sudo apt-get update
sudo apt-get install -y curl git build-essential ca-certificates gnupg

# 2. Python 3.11+
sudo apt-get install -y python3.11 python3.11-venv python3-pip
python3.11 --version

# 3. Node.js 20 LTS (via nvm, avoids sudo/version conflicts)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 20
node --version && npm --version

# 4. Docker (for local container builds + Cloud Run parity)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER   # log out/in after this
docker --version

# 5. Google Cloud CLI
curl -sSL https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud --version

# 6. Authenticate
gcloud auth login
gcloud auth application-default login
```

**Definition of done:** all six version commands above print a version with no errors.

---

## 8. Build order (follow sequentially)

Do not start with the UI or with agents. Build ground truth and data first — it is the foundation the benchmark depends on.

### Phase 1 — GCP project setup

```bash
export PROJECT_ID="migrationproof-<yourname>-2026"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Link billing (use the $300 trial credit account)
gcloud beta billing projects link $PROJECT_ID --billing-account=<BILLING_ACCOUNT_ID>

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  generativelanguage.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com
```

Create a service account for the backend:

```bash
gcloud iam service-accounts create migrationproof-backend \
  --display-name="MigrationProof Backend"

SA_EMAIL="migrationproof-backend@${PROJECT_ID}.iam.gserviceaccount.com"

for role in roles/bigquery.dataEditor roles/bigquery.jobUser \
            roles/storage.objectAdmin roles/secretmanager.secretAccessor \
            roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" --role="$role"
done
```

Create GCS buckets and BigQuery dataset:

```bash
gsutil mb -l us-central1 gs://${PROJECT_ID}-artifacts
gsutil mb -l us-central1 gs://${PROJECT_ID}-synthetic-data

bq mk --dataset --location=us-central1 ${PROJECT_ID}:migrationproof
```

Store the Gemini API key in Secret Manager (never commit it):

```bash
echo -n "<YOUR_GEMINI_API_KEY>" | gcloud secrets create gemini-api-key --data-file=-
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor"
```

**Definition of done:** `gcloud services list --enabled` shows all APIs above; `bq ls` shows the `migrationproof` dataset; both GCS buckets exist; the secret exists and the service account can access it.

#### Environment variables (`.env.example`)

```bash
GCP_PROJECT_ID=migrationproof-<yourname>-2026
GCP_REGION=us-central1
BQ_DATASET=migrationproof
GCS_ARTIFACT_BUCKET=<PROJECT_ID>-artifacts
GCS_SYNTHETIC_BUCKET=<PROJECT_ID>-synthetic-data
GEMINI_API_KEY=              # local dev only; prod uses Secret Manager
GEMINI_MODEL=gemini-2.0-flash
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=          # set a strong value, never commit real value
ENVIRONMENT=local            # local | production
```

### Phase 2 — BigQuery schema

Create these tables in the `migrationproof` dataset (DDL lives in `infra/bigquery/schema/`):

- **`entities`** — `entity_id, name, type (service|database|vm|dns|external_api), metadata (JSON), source_artifact, created_at`
- **`dependencies`** — `dependency_id, source_entity_id, target_entity_id, dependency_type, confidence, status (candidate|verified|rejected), created_at`
- **`evidence`** — `evidence_id, dependency_id, artifact_uri, artifact_type, quoted_snippet, extracted_by (agent name), created_at`
- **`migration_waves`** — `wave_id, wave_number, entity_id, scenario_id`
- **`ground_truth`** — `scenario_id, entity_id_a, entity_id_b, is_dependency (bool), expected_wave_conflict (bool), failure_type` (used only by the benchmark, never by the runtime verification engine)
- **`verification_results`** — `result_id, scenario_id, wave_number, decision (ALLOW|BLOCK), reasons (JSON), confidence, blast_radius (JSON), created_at`
- **`llm_call_log`** — `call_id, agent, model, prompt_tokens, completion_tokens, latency_ms, created_at` (for cost tracking)

**Definition of done:** all 7 tables exist with correct schemas; a smoke-test script can insert and query one row from each.

### Phase 3 — Synthetic dataset + ground truth

Build `backend/scripts/generate_synthetic_data.py` to generate one fictional company ("RetailCo") environment:

```
RetailCo
├── frontend, checkout-api, order-service, payment-service
├── mysql-prod, redis, kafka
├── dns records, load-balancer, monitoring
└── external payment API
```

Artifacts to generate (as files, uploaded to `GCS_SYNTHETIC_BUCKET`):
`vm_inventory.csv`, `dns_records.csv`, `network_connections.csv`, `application_config.json`, `architecture.md`, `migration_plan.json`, `service_catalog.csv`.

Generate **at least 8 distinct scenarios** with deliberately seeded, known outcomes, each labeled in `ground_truth`:

1. Correct/safe migration plan
2. Database moved after the application that depends on it
3. Stale DNS still pointing at the old endpoint
4. Hidden dependency buried inside a config file
5. Forgotten external API dependency
6. Two services assigned to incompatible waves
7. Stale/outdated inventory data
8. Contradictory evidence across two artifacts

Aim for ~40 safe and ~60 unsafe scenarios total for a statistically meaningful benchmark (Phase 7).

**Definition of done:** synthetic artifacts exist in GCS; `ground_truth` table is populated; scenario count and safe/unsafe split are logged in `docs/BENCHMARK_RESULTS.md` (initially empty results, filled in Phase 7).

### Phase 4 — Discovery + Evidence agents (Gemini + ADK)

Implement `discovery_agent.py` and `evidence_agent.py`:

- Input: artifacts pulled from GCS for a given scenario.
- Output: JSON-schema-validated entities + candidate dependencies + evidence, written to BigQuery (`entities`, `dependencies` with `status='candidate'`, `evidence`).
- Every dependency **must** have ≥1 evidence row or it is dropped before reaching the verification engine.
- Log every call to `llm_call_log`.

**Definition of done:** running the pipeline against one synthetic scenario populates `entities`/`dependencies`/`evidence` with plausible, evidence-backed rows; unit tests cover JSON schema validation and the "no evidence → dropped" rule.

### Phase 5 — Deterministic verification engine

Implement `backend/app/verification/`:

- `graph.py`: builds a dependency graph from `entities`/`dependencies` (verified only).
- `rules.py`: deterministic checks —
  - cross-wave dependency violation (dependency's wave > dependent's wave)
  - stale reference detection (evidence timestamp older than a threshold, or contradicts newer evidence)
  - contradiction detection (two evidence sources disagree on the same dependency)
  - missing-dependency heuristic flagged for human review (not auto-blocked)
- `blast_radius.py`: graph traversal from a blocked entity to all downstream dependents.
- `confidence.py`: aggregate evidence-source count/type into a confidence score.
- Output written to `verification_results`.

**Definition of done:** unit tests cover each rule independently with hand-crafted graph fixtures (no LLM involved); given a synthetic scenario's verified graph + plan, the engine produces the expected ALLOW/BLOCK matching `ground_truth`.

### Phase 6 — Analysis Agent (narrative layer)

Implement `analysis_agent.py`: takes the verification engine's structured output and produces the human-readable explanation shown in the UI (reasons, evidence summary, recommendation text). This agent **never changes the decision** — it only narrates it.

**Definition of done:** given a fixed verification result, the agent produces coherent, evidence-consistent prose; a test asserts the agent cannot alter `decision` or `confidence` fields (schema-enforced, decision fields excluded from its output).

### Phase 7 — Benchmark

Implement `backend/benchmark/run_benchmark.py`:

- Runs the full pipeline (Phases 4–6) against all synthetic scenarios.
- Compares `verification_results` against `ground_truth`.
- Computes and writes to `docs/BENCHMARK_RESULTS.md`:
  - Dependency recall/precision
  - Unsafe-approval rate (safety-critical false negatives)
  - Contradiction-detection accuracy
  - Blast-radius accuracy (precision/recall vs. known downstream set)
  - Per-scenario pass/fail table

**Definition of done:** benchmark runs end-to-end via a single command and produces `docs/BENCHMARK_RESULTS.md` with real numbers (not placeholders) from the synthetic scenario set.

### Phase 8 — FastAPI backend

Endpoints (all under `backend/app/api/`):

- `POST /artifacts/upload` — upload artifact(s) to GCS for a scenario/project
- `POST /discovery/run` — trigger discovery+evidence agents for a project
- `GET /entities`, `GET /dependencies`, `GET /evidence` — inspection endpoints
- `POST /verify` — run verification engine for a given migration plan/wave
- `GET /verify/{result_id}` — fetch a verification result
- `GET /waves/{project_id}` — fetch migration plan/waves
- `GET /health` — liveness/readiness

All endpoints behind the fixed-credential auth middleware except `/health`. CORS restricted to the deployed frontend origin (and `localhost` in dev).

**Definition of done:** `pytest backend/tests` passes; `curl` against each endpoint (documented in `docs/ARCHITECTURE.md`) returns expected status codes locally.

### Phase 9 — React frontend

Screens:

1. **Login** — single fixed username/password form.
2. **Upload/Project** — upload artifacts, list existing projects/scenarios.
3. **Migration Plan / Wave Review** — view proposed waves and entities.
4. **Verify** — trigger verification, show loading state.
5. **Result** — ALLOW (green) / BLOCK (red) banner, evidence list, blast-radius diagram, recommendation text (matches the mockups in Section 1).

**Definition of done:** `npm run build` succeeds; a manual walkthrough (upload → verify → see BLOCK with evidence) works against the local backend.

### Phase 10 — Deployment (Cloud Run)

See [Section 12](#12-deployment-cloud-run) below.

### Phase 11 — Demo scenario + documentation

Pick the single most compelling BLOCK scenario (recommended: "database moved after the application that depends on it") as the primary demo. Write the walkthrough into `docs/DEMO_SCRIPT.md`. Finalize `docs/ARCHITECTURE.md` and this README's status.

---

## 9. Local development

```bash
# Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # fill in values
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # proxies API calls to http://localhost:8080

# Tests
cd backend && pytest tests/unit tests/integration -v

# Benchmark
cd backend && python -m benchmark.run_benchmark
```

---

## 10. Authentication (dashboard)

- No OAuth/user accounts for the MVP.
- The frontend shows a login screen requiring `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`.
- The backend validates a session (signed cookie or simple bearer token issued on login) on all non-`/health` routes.
- Credentials are set via environment variables / Secret Manager — **never hardcoded**, never logged, never committed.

---

## 11. Cost controls

- Use `gemini-2.0-flash` (or the cheapest suitable model) for extraction; reserve larger models only if extraction quality genuinely requires it.
- Cache discovery/evidence results per scenario in BigQuery; do not re-run the LLM pipeline on unchanged artifacts.
- Log token usage (`llm_call_log`) and check it before/after the benchmark run.
- Set a Cloud Billing budget alert (e.g. $20/$50/$100 thresholds) on the trial-credit account.
- Avoid autoscaling Cloud Run to high max instances during development — cap `--max-instances` at a low number (e.g. 2) for the demo service.

---

## 12. Deployment (Cloud Run)

Backend:

```bash
cd backend
gcloud builds submit --tag gcr.io/${PROJECT_ID}/migrationproof-backend

gcloud run deploy migrationproof-backend \
  --image gcr.io/${PROJECT_ID}/migrationproof-backend \
  --region us-central1 \
  --service-account $SA_EMAIL \
  --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=${PROJECT_ID},BQ_DATASET=migrationproof" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,DASHBOARD_PASSWORD=dashboard-password:latest" \
  --max-instances=2 \
  --allow-unauthenticated
```

Frontend:

```bash
cd frontend
# Build with backend URL baked in via Vite env var
VITE_API_BASE_URL=https://<backend-cloud-run-url> npm run build

gcloud builds submit --tag gcr.io/${PROJECT_ID}/migrationproof-frontend
gcloud run deploy migrationproof-frontend \
  --image gcr.io/${PROJECT_ID}/migrationproof-frontend \
  --region us-central1 \
  --max-instances=2 \
  --allow-unauthenticated
```

**Deployment verification checklist:**

- [ ] `curl https://<backend-url>/health` returns `200`
- [ ] Frontend loads and shows the login screen
- [ ] Logging in with the fixed credentials succeeds
- [ ] Uploading a synthetic scenario's artifacts succeeds
- [ ] Running `/verify` on a known-unsafe scenario returns `BLOCK` with evidence, matching ground truth
- [ ] Running `/verify` on a known-safe scenario returns `ALLOW`
- [ ] CORS is locked to the frontend's Cloud Run origin (no `*`)

---

## 13. Testing strategy

- **Unit tests**: verification rules (`rules.py`, `blast_radius.py`, `confidence.py`) tested against hand-crafted graph fixtures — no network/LLM calls.
- **Integration tests**: FastAPI endpoints tested with a test BigQuery dataset/GCS bucket (or mocked clients).
- **Benchmark**: full pipeline run against all synthetic scenarios, compared to `ground_truth` (Phase 7).
- Run `pytest` and the benchmark before every deployment.

---

## 14. Submission checklist (Patchamomma 2026)

- [ ] Deployed frontend URL is reachable and login works with fixed credentials
- [ ] End-to-end demo scenario works live (upload → verify → BLOCK with evidence)
- [ ] `docs/BENCHMARK_RESULTS.md` has real numbers, not placeholders
- [ ] `docs/ARCHITECTURE.md` finalized
- [ ] `docs/DEMO_SCRIPT.md` finalized (script for the recorded/live demo)
- [ ] README reflects actual final architecture (update any deviations from plan)
- [ ] Billing budget alerts configured; no exposed secrets in the repo (`git log -p | grep -i key` clean)
- [ ] Progress-form fields (data source, GCP services used, AI details, tech stack, vibe-coding tools, billing) match what was actually built

---

## 15. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `gcloud` commands fail with permission errors | Not authenticated / wrong project | `gcloud auth login`, `gcloud config set project $PROJECT_ID` |
| BigQuery insert fails silently | Schema mismatch | Compare payload against `infra/bigquery/schema/*.json` |
| Gemini calls return empty/invalid JSON | Prompt not enforcing schema strictly enough | Add explicit JSON schema + retry-with-validation in agent code |
| Cloud Run deploy succeeds but 502s | Container not listening on `$PORT` | Ensure Uvicorn binds to `0.0.0.0:$PORT` (Cloud Run injects `PORT`) |
| CORS errors in browser console | Frontend origin not whitelisted on backend | Update backend CORS allowed origins with the deployed frontend URL |
| Verification engine disagrees with ground truth | Rule bug, or upstream extraction produced no/duplicate evidence | Check `evidence` table for the dependency before blaming the rule engine |
| `/healthz` returns a generic Google HTML 404 (not your app's JSON) on the deployed Cloud Run URL | `/healthz` is a reserved path intercepted at the Google Frontend/Cloud Run edge and never forwarded to your container | Use a different path for the health endpoint (this project uses `/health`, not `/healthz`) |

---

## 16. Status

Updated as work progresses — only checked after each Definition of Done is actually met.

- [x] Phase 1 — GCP project setup (`migrationguard-sv`: APIs, SA + IAM, buckets, dataset)
- [x] Phase 2 — BigQuery schema (7 tables live in `migrationproof` dataset)
- [x] Phase 3 — Synthetic dataset + ground truth (8 scenarios generated, uploaded to GCS, loaded to BigQuery)
- [x] Phase 4 — Discovery + Evidence agents (implemented + unit-tested; **live via Vertex AI** — verified end-to-end: 28 entities, 18 evidence-backed dependencies extracted from real artifacts)
- [x] Phase 5 — Deterministic verification engine (rules + graph + blast radius + confidence; 9/9 unit tests passing)
- [x] Phase 6 — Analysis agent (implemented; **live via Vertex AI** — produces the narrative on every `/verify` call)
- [x] Phase 7 — Benchmark (8/8 scenarios pass: 100% accuracy, 0% unsafe-approval — against seeded reference data, see `docs/BENCHMARK_RESULTS.md` note)
- [x] Phase 8 — FastAPI backend (14/14 tests; verified live via curl on Cloud Run)
- [x] Phase 9 — React frontend (login + project + waves + result screens; production build passing)
- [x] Phase 10 — Cloud Run deployment (backend + frontend live; all 7 checklist items pass, incl. CORS)
- [x] Phase 11 — Demo scenario + docs (`docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`)

### Deployed URLs

- **Frontend (submit this):** https://migrationproof-frontend-509319730686.us-central1.run.app
- **Backend:** https://migrationproof-backend-509319730686.us-central1.run.app

### Remaining before submission

- [ ] Set a Cloud Billing budget alert on the trial account.
- [ ] Update the Patchamomma form fields to match what was actually built.

### Gemini backend

The LLM layer runs on **Vertex AI** (`GEMINI_BACKEND=vertexai`, model
`gemini-2.5-flash`), authenticated with the project's service account and
billed to the GCP project (your $300 trial) — no AI Studio API key needed.
To use an AI Studio API key instead, set `GEMINI_BACKEND=api_key` and
`GEMINI_API_KEY` (Secret Manager `gemini-api-key` in prod).
