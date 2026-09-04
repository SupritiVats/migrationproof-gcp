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

## What is *not* yet wired up (be honest if asked)

- **Discovery / Evidence agents** are implemented and unit-tested, but the
  *live* Gemini calls require a `GEMINI_API_KEY` that was not configured at
  demo time. The benchmark currently runs against seeded reference data that
  represents what those agents are designed to produce from the same raw
  artifacts (which are already uploaded to GCS). The `/verify` endpoint
  degrades gracefully: without a key, `narrative` is simply `null` while the
  deterministic decision, reasons, and evidence remain fully functional.
- The **Analysis agent** narrative therefore won't appear in the demo unless a
  Gemini key is added to Secret Manager and the backend env updated.

## To enable the live LLM layer later

```bash
echo -n "<GEMINI_API_KEY>" | gcloud secrets create gemini-api-key \
  --data-file=- --project=migrationguard-sv
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:migrationproof-backend@migrationguard-sv.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" --project=migrationguard-sv

gcloud run services update migrationproof-backend \
  --region us-central1 --project=migrationguard-sv \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest"
```
Then re-run `python -m benchmark.run_benchmark` for true end-to-end numbers
(Gemini extraction → deterministic verification → ground truth).
