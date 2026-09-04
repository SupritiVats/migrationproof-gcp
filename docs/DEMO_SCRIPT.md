# MigrationProof — Demo Script

**Live URL (frontend):** https://migrationproof-frontend-509319730686.us-central1.run.app

**Credentials (fixed dashboard login):**
- Username: `admin`
- Password: see `backend/.secrets_dashboard_password_DO_NOT_COMMIT.txt` (or Secret Manager `dashboard-password` in project `migrationguard-sv`)

> The dashboard is intentionally not open to unauthenticated browsing: the
> login screen is the first thing a judge sees. Hand them these credentials.

---

## The killer demo (recommended)

The single most compelling scenario is **`scn-02-db-migrated-after-app`**:
a service (`checkout-api`) is scheduled for Wave 1, but the database it
depends on (`mysql-prod`) is scheduled for Wave 3 — a classic, real-world
cutover mistake that takes systems down.

### Steps

1. Open the frontend URL. You'll see the login screen.
2. Sign in with the credentials above.
3. On the Project page, set **Project / scenario ID** to
   `scn-02-db-migrated-after-app` and click **Load project**.
4. Scroll to **Migration plan / waves** — you should see the proposed waves.
5. Click **Verify Wave 1**.
6. Expected result: a red **🔴 MIGRATION BLOCKED** banner, reason
   `cross_wave_dependency`, message about `checkout-api` (Wave 1) depending on
   `mysql-prod` (Wave 3), confidence 90%.
7. Now repeat with **`scn-01-safe-migration`** → **Verify Wave 1** → you should
   get a green **🟢 SAFE TO MIGRATE** banner.

### Talking points while it runs

- *"This is not a migration planner — Google Migration Center already does
  discovery and planning. This is a verification layer: show me the evidence
  that proves this plan is safe."*
- *"The final ALLOW/BLOCK decision is not made by Gemini. Gemini only extracts
  structured claims and evidence from messy artifacts; a deterministic graph +
  rules engine makes the safety call — that's what makes it auditable and
  testable."*
- *"We benchmarked this against controlled synthetic scenarios with known
  ground truth — not just a demo, an engineering experiment."* (Show
  `docs/BENCHMARK_RESULTS.md`.)

---

## Secondary scenarios (if time permits)

| Scenario ID | What it demonstrates | Expected |
|---|---|---|
| `scn-03-stale-dns-reference` | Contradictory evidence: config still references a DNS record marked decommissioned | BLOCK (`contradictory_evidence`) |
| `scn-08-contradictory-evidence-queue` | Config says kafka is active; architecture doc says it was decommissioned | BLOCK (`contradictory_evidence`) |
| `scn-06-incompatible-waves-two-services` | `order-service` (Wave 1) depends on `checkout-api` (Wave 2) | BLOCK (`cross_wave_dependency`) |
| `scn-04-hidden-dependency-in-config` | Weak evidence for a dependency → flagged for human review, but not auto-blocked | ALLOW (advisory reason shown) |
| `scn-05-forgotten-external-dependency` | Dependency on an external API outside migration scope | ALLOW |

---

## The LLM layer is live

The Gemini/ADK agents run on **Vertex AI** (service-account auth, billed to
the project's trial credits — no AI Studio key needed). Verified end-to-end:

- The **Analysis agent** produces the narrative on every `/verify` call —
  you should see a plain-English "Explanation" card on the result screen.
- The **Discovery + Evidence agents** work live: "Run discovery" on a project
  with uploaded artifacts will extract entities/dependencies into BigQuery
  and quote evidence for each.
- **Known limitation:** the benchmark's 100% numbers come from hand-seeded
  reference data (the ground truth the agents are *supposed* to reproduce).
  A true end-to-end benchmark (raw artifacts → Gemini extraction →
  verification) will show lower accuracy — that's the honest, expected gap
  between extraction recall and decision correctness.

## LLM backend config

The deployed backend uses `GEMINI_BACKEND=vertexai` + `GEMINI_MODEL=gemini-2.5-flash`
(Vertex AI, service-account auth, project billing). To use an AI Studio API
key instead, set `GEMINI_BACKEND=api_key` and a `GEMINI_API_KEY` secret.
