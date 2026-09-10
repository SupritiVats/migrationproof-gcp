import { useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";

const HOW_TO_STEPS = [
  {
    title: "Sign in",
    body: "Use the credentials you were given for this demo.",
  },
  {
    title: "Load a project",
    body: "On the Project page, type a project / scenario ID and click Load project. Use one of the 8 pre-loaded demo scenarios below, or any ID of your own.",
  },
  {
    title: "Upload artifacts (optional)",
    body: "To test live AI extraction instead of a pre-loaded scenario, upload raw infrastructure files: vm_inventory.csv, dns_records.csv, network_connections.csv, application_config.json, architecture.md, service_catalog.csv, migration_plan.json. You can delete a file (or clear all) any time.",
  },
  {
    title: "Run discovery (optional)",
    body: "Click Run discovery to have the Gemini agents read your uploaded artifacts and extract entities, dependencies, and cited evidence into BigQuery. Skip this for pre-loaded scenarios — their data is already there.",
  },
  {
    title: "Review the migration plan",
    body: "The Migration plan / waves card shows which services are scheduled in which wave.",
  },
  {
    title: "Verify a wave",
    body: "Click Verify Wave N. You'll see SAFE TO MIGRATE or MIGRATION BLOCKED, with the exact reason, a confidence score, blast radius, and a plain-English explanation.",
  },
];

const SCENARIOS: [string, "ALLOW" | "BLOCK", string][] = [
  ["scn-01-safe-migration", "ALLOW", "All dependencies co-scheduled correctly"],
  ["scn-02-db-migrated-after-app", "BLOCK", "App migrates before its database"],
  ["scn-03-stale-dns-reference", "BLOCK", "Contradictory evidence (decommissioned DNS)"],
  ["scn-04-hidden-dependency-in-config", "ALLOW", "Weak evidence flagged for review, not auto-blocked"],
  ["scn-05-forgotten-external-dependency", "ALLOW", "Dependency outside migration scope"],
  ["scn-06-incompatible-waves-two-services", "BLOCK", "Two interdependent services in different waves"],
  ["scn-07-stale-inventory-no-impact", "ALLOW", "Stale but non-contradictory inventory data"],
  ["scn-08-contradictory-evidence-queue", "BLOCK", "Config vs. architecture doc disagree"],
];

const LINKS = [
  { icon: "✉️", label: "supritivats123@gmail.com", href: "mailto:supritivats123@gmail.com" },
  { icon: "💼", label: "linkedin.com/in/supriti-vats", href: "https://www.linkedin.com/in/supriti-vats/" },
  { icon: "🌐", label: "supriti-vats-portfolio.netlify.app", href: "https://supriti-vats-portfolio.netlify.app/" },
  { icon: "🐙", label: "github.com/SupritiVats", href: "https://github.com/SupritiVats" },
];

export default function AboutPage() {
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <NavBar />

      <div className="card">
        <h2>
          <span className="section-icon">🛡️</span>What is MigrationProof?
        </h2>
        <p style={{ color: "#c9d1d9" }}>
          An <strong>evidence-grounded verification layer</strong> for cloud migration plans.
          Before a team cuts over a batch of services ("a wave") to new infrastructure,
          MigrationProof checks whether that plan is actually safe — and gives a hard{" "}
          <strong>ALLOW / BLOCK</strong> decision backed by cited evidence, not a guess.
        </p>
        <p style={{ color: "var(--muted)" }}>
          This is deliberately <em>not</em> a migration planner or a dependency-discovery tool —
          those already exist. MigrationProof's job is narrower: independently challenge a
          proposed plan and demand proof before approving it.
        </p>
      </div>

      <div className="card">
        <h2>
          <span className="section-icon">🧭</span>How it works
        </h2>
        <div className="pipeline">
          <div className="pipeline-node">
            <div className="pipeline-title">Artifacts</div>
            <div className="pipeline-sub">GCS</div>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node ai">
            <div className="pipeline-title">Discovery Agent</div>
            <div className="pipeline-sub">Gemini · candidates</div>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node ai">
            <div className="pipeline-title">Evidence Agent</div>
            <div className="pipeline-sub">Gemini · quotes proof</div>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node data">
            <div className="pipeline-title">BigQuery</div>
            <div className="pipeline-sub">entities · deps · evidence</div>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node decision">
            <div className="pipeline-title">Verification Engine</div>
            <div className="pipeline-sub">graph + rules</div>
            <div className="no-ai-flag">NO AI · DETERMINISTIC</div>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node">
            <div className="pipeline-title">ALLOW / BLOCK</div>
            <div className="pipeline-sub">reasons · confidence</div>
          </div>
          <span className="pipeline-arrow">→</span>
          <div className="pipeline-node ai">
            <div className="pipeline-title">Analysis Agent</div>
            <div className="pipeline-sub">Gemini · narrates only</div>
          </div>
        </div>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          <strong style={{ color: "#e6edf3" }}>Gemini never makes the safety decision.</strong> It
          only extracts structured, cited facts. A separate deterministic rules engine applies the
          actual logic — explainable, reproducible, and benchmarked against scenarios with known
          correct answers.
        </p>
      </div>

      <div className="card">
        <h2>
          <span className="section-icon">📋</span>How to use — step by step
        </h2>
        <div className="stepper">
          {HOW_TO_STEPS.map((step, i) => (
            <div className="stepper-item" key={step.title}>
              <div className="stepper-line" />
              <div className="stepper-circle">{i + 1}</div>
              <div className="stepper-content">
                <h4>{step.title}</h4>
                <p>{step.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>
          <span className="section-icon">🧪</span>Pre-loaded demo scenarios
        </h2>
        <p style={{ color: "var(--muted)", fontSize: 13, marginTop: -8 }}>
          Click a row to load it on the Project page.
        </p>
        <table className="scenario-table">
          <thead>
            <tr style={{ color: "var(--muted)", textAlign: "left" }}>
              <th>Scenario ID</th>
              <th>Result</th>
              <th>What it demonstrates</th>
            </tr>
          </thead>
          <tbody>
            {SCENARIOS.map(([id, result, note]) => (
              <tr
                key={id}
                className={`scenario-row ${result === "ALLOW" ? "allow" : "block"}`}
                onClick={() => navigate(`/project?scenario=${id}`)}
              >
                <td style={{ fontFamily: "monospace" }}>{id}</td>
                <td>
                  <span className={`badge ${result === "ALLOW" ? "result-allow" : "result-block"}`}>
                    {result === "ALLOW" ? "🟢 ALLOW" : "🔴 BLOCK"}
                  </span>
                </td>
                <td style={{ color: "var(--muted)" }}>{note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>
          <span className="section-icon">👩‍💻</span>Developed by
        </h2>
        <div className="profile-card">
          <div className="profile-avatar">SV</div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>Supriti Vats</div>
            <div className="profile-links">
              {LINKS.map((link) => (
                <a key={link.href} href={link.href} target="_blank" rel="noreferrer" className="profile-link">
                  <span>{link.icon}</span>
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
