import NavBar from "../components/NavBar";

const STEP_CARD_STYLE: React.CSSProperties = { background: "#0b0f14", marginBottom: 12 };

export default function AboutPage() {
  return (
    <div className="app-shell">
      <NavBar />

      <div className="card">
        <h2>What is MigrationProof?</h2>
        <p style={{ color: "#c9d1d9" }}>
          MigrationProof is an <strong>evidence-grounded verification layer</strong> for cloud
          migration plans. Before a team cuts over a batch of services ("a wave") to new
          infrastructure, MigrationProof checks whether that plan is actually safe — and gives a
          hard <strong>ALLOW / BLOCK</strong> decision backed by cited evidence, not a guess.
        </p>
        <p style={{ color: "#8b98a5" }}>
          This is deliberately <em>not</em> a migration planner or a dependency-discovery tool —
          those already exist (e.g. Google Cloud Migration Center). MigrationProof's job is
          narrower: independently challenge a proposed plan and demand proof before approving it.
        </p>
      </div>

      <div className="card">
        <h2>How it works — the architecture</h2>
        <pre style={{ background: "#0b0f14", padding: 16, borderRadius: 8, overflowX: "auto", fontSize: 12, color: "#8b98a5" }}>
{`Raw artifacts (GCS)
      │
      ▼
Discovery Agent (Gemini/ADK) ──► candidate entities + dependencies
      │
      ▼
Evidence Agent (Gemini/ADK) ──► quoted proof for each dependency
      │              (no evidence = dropped, never reaches the decision)
      ▼
BigQuery (entities, dependencies, evidence, migration waves)
      │
      ▼
Deterministic Verification Engine  ◄── pure rules + graph logic, NO AI
      │                                  (cross-wave conflicts, contradictions,
      ▼                                   low-confidence flags, blast radius)
ALLOW / BLOCK + reasons + confidence
      │
      ▼
Analysis Agent (Gemini) — writes a plain-English narrative
                            of the decision that was ALREADY made`}
        </pre>
        <p style={{ color: "#8b98a5" }}>
          The key design decision: <strong>Gemini never makes the safety decision.</strong> It only
          extracts structured, cited facts from messy artifacts. A separate deterministic rules
          engine applies the actual logic — which makes the result explainable, reproducible, and
          testable (we benchmark it against scenarios with known correct answers).
        </p>
      </div>

      <div className="card">
        <h2>How to use this app — step by step</h2>

        <div className="card" style={STEP_CARD_STYLE}>
          <strong>Step 1 — Sign in</strong>
          <p style={{ color: "#8b98a5", margin: "6px 0 0" }}>Use the credentials you were given for this demo.</p>
        </div>

        <div className="card" style={STEP_CARD_STYLE}>
          <strong>Step 2 — Load a project</strong>
          <p style={{ color: "#8b98a5", margin: "6px 0 0" }}>
            On the Project page, type a project / scenario ID and click <strong>Load project</strong>.
            You can use one of the 8 pre-loaded demo scenarios (see below) or a project ID of your
            own choosing.
          </p>
        </div>

        <div className="card" style={STEP_CARD_STYLE}>
          <strong>Step 3 (optional) — Upload your own artifacts</strong>
          <p style={{ color: "#8b98a5", margin: "6px 0 0" }}>
            If you want to test the live AI extraction instead of a pre-loaded scenario, upload
            raw infrastructure files: <code>vm_inventory.csv</code>, <code>dns_records.csv</code>,
            <code> network_connections.csv</code>, <code>application_config.json</code>,{" "}
            <code>architecture.md</code>, <code>service_catalog.csv</code>,{" "}
            <code>migration_plan.json</code>. You can delete an uploaded file (or clear all) if you
            make a mistake — no need to redeploy anything.
          </p>
        </div>

        <div className="card" style={STEP_CARD_STYLE}>
          <strong>Step 4 (optional) — Run discovery</strong>
          <p style={{ color: "#8b98a5", margin: "6px 0 0" }}>
            Click <strong>Run discovery</strong> to have the Gemini Discovery + Evidence agents
            read your uploaded artifacts and extract entities, dependencies, and cited evidence
            into BigQuery. Skip this step for the pre-loaded demo scenarios — their data is already
            there.
          </p>
        </div>

        <div className="card" style={STEP_CARD_STYLE}>
          <strong>Step 5 — Review the migration plan</strong>
          <p style={{ color: "#8b98a5", margin: "6px 0 0" }}>
            The <strong>Migration plan / waves</strong> card shows which services are scheduled in
            which wave.
          </p>
        </div>

        <div className="card" style={STEP_CARD_STYLE}>
          <strong>Step 6 — Verify a wave</strong>
          <p style={{ color: "#8b98a5", margin: "6px 0 0" }}>
            Click <strong>Verify Wave N</strong>. You'll see 🟢 SAFE TO MIGRATE or 🔴 MIGRATION
            BLOCKED, with the exact reason, a confidence score, and a plain-English explanation
            written by the Analysis agent.
          </p>
        </div>
      </div>

      <div className="card">
        <h2>Pre-loaded demo scenarios</h2>
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ color: "#8b98a5", textAlign: "left" }}>
              <th style={{ paddingBottom: 8 }}>Scenario ID</th>
              <th style={{ paddingBottom: 8 }}>Expected result</th>
              <th style={{ paddingBottom: 8 }}>What it demonstrates</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["scn-01-safe-migration", "ALLOW", "All dependencies co-scheduled correctly"],
              ["scn-02-db-migrated-after-app", "BLOCK", "App migrates before its database"],
              ["scn-03-stale-dns-reference", "BLOCK", "Contradictory evidence (decommissioned DNS)"],
              ["scn-04-hidden-dependency-in-config", "ALLOW", "Weak evidence flagged for review, not auto-blocked"],
              ["scn-05-forgotten-external-dependency", "ALLOW", "Dependency outside migration scope"],
              ["scn-06-incompatible-waves-two-services", "BLOCK", "Two interdependent services in different waves"],
              ["scn-07-stale-inventory-no-impact", "ALLOW", "Stale but non-contradictory inventory data"],
              ["scn-08-contradictory-evidence-queue", "BLOCK", "Config vs. architecture doc disagree"],
            ].map(([id, result, note]) => (
              <tr key={id} style={{ borderTop: "1px solid #202b36" }}>
                <td style={{ padding: "8px 0", fontFamily: "monospace" }}>{id}</td>
                <td style={{ padding: "8px 0" }}>
                  <span className="badge" style={{ background: result === "ALLOW" ? "#113a24" : "#3a1414", color: result === "ALLOW" ? "#4ade80" : "#f87171" }}>
                    {result}
                  </span>
                </td>
                <td style={{ padding: "8px 0", color: "#8b98a5" }}>{note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Developed by</h2>
        <p style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Supriti Vats</p>
        <p style={{ color: "#8b98a5", margin: "4px 0" }}>
          Email:{" "}
          <a href="mailto:supritivats123@gmail.com" style={{ color: "#4a90ff" }}>
            supritivats123@gmail.com
          </a>
        </p>
        <p style={{ color: "#8b98a5", margin: "4px 0" }}>
          LinkedIn:{" "}
          <a href="https://www.linkedin.com/in/supriti-vats/" target="_blank" rel="noreferrer" style={{ color: "#4a90ff" }}>
            linkedin.com/in/supriti-vats
          </a>
        </p>
        <p style={{ color: "#8b98a5", margin: "4px 0" }}>
          Portfolio:{" "}
          <a href="https://supriti-vats-portfolio.netlify.app/" target="_blank" rel="noreferrer" style={{ color: "#4a90ff" }}>
            supriti-vats-portfolio.netlify.app
          </a>
        </p>
        <p style={{ color: "#8b98a5", margin: "4px 0" }}>
          GitHub:{" "}
          <a href="https://github.com/SupritiVats" target="_blank" rel="noreferrer" style={{ color: "#4a90ff" }}>
            github.com/SupritiVats
          </a>
        </p>
      </div>
    </div>
  );
}
