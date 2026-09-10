import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  deleteAllArtifacts,
  deleteArtifact,
  listArtifacts,
  listWaves,
  runDiscovery,
  uploadArtifact,
} from "../api/client";
import NavBar from "../components/NavBar";

const DEMO_SCENARIOS = [
  "scn-01-safe-migration",
  "scn-02-db-migrated-after-app",
  "scn-03-stale-dns-reference",
  "scn-04-hidden-dependency-in-config",
  "scn-05-forgotten-external-dependency",
  "scn-06-incompatible-waves-two-services",
  "scn-07-stale-inventory-no-impact",
  "scn-08-contradictory-evidence-queue",
];

function filenameFromUri(uri: string): string {
  return uri.split("/").pop() || uri;
}

function fileIcon(filename: string): string {
  if (filename.endsWith(".csv")) return "📊";
  if (filename.endsWith(".json")) return "🧩";
  if (filename.endsWith(".md")) return "📄";
  return "📁";
}

interface StepProps {
  index: number;
  label: string;
  active: boolean;
  done: boolean;
}

function ProgressStep({ index, label, active, done }: StepProps) {
  return (
    <div className={`progress-step ${active ? "active" : ""} ${done ? "done" : ""}`}>
      <div className="progress-step-circle">{done ? "✓" : index}</div>
      <div className="progress-step-label">{label}</div>
    </div>
  );
}

export default function ProjectPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [projectId, setProjectId] = useState("scn-02-db-migrated-after-app");
  const [loaded, setLoaded] = useState(false);
  const [artifacts, setArtifacts] = useState<string[]>([]);
  const [waves, setWaves] = useState<{ entity_id: string; wave_number: number }[]>([]);
  const [discoveryDone, setDiscoveryDone] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh(idOverride?: string) {
    const id = idOverride ?? projectId;
    setError(null);
    try {
      const [artifactsResult, wavesResult] = await Promise.all([listArtifacts(id), listWaves(id)]);
      setArtifacts(artifactsResult.artifacts);
      setWaves(wavesResult.waves);
      setLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    }
  }

  useEffect(() => {
    const scenario = searchParams.get("scenario");
    if (scenario) {
      setProjectId(scenario);
      refresh(scenario);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadArtifact(projectId, file);
      setStatus(`Uploaded ${file.name}.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function handleDeleteArtifact(uri: string) {
    const filename = filenameFromUri(uri);
    setBusy(true);
    setError(null);
    try {
      await deleteArtifact(projectId, filename);
      setStatus(`Deleted ${filename}.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteAll() {
    if (!confirm(`Delete all ${artifacts.length} uploaded artifact(s) for "${projectId}"?`)) return;
    setBusy(true);
    setError(null);
    try {
      const result = await deleteAllArtifacts(projectId);
      setStatus(`Deleted ${result.deleted_count} artifact(s).`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRunDiscovery() {
    setBusy(true);
    setError(null);
    setStatus("Running Gemini Discovery + Evidence agents... this can take 10-30 seconds.");
    try {
      const result = await runDiscovery(projectId);
      setStatus(
        `Discovery complete — ${result.entities_discovered} entities, ` +
          `${result.dependencies_verified} evidence-backed dependencies ` +
          `(${result.dependencies_dropped_no_evidence} dropped for lack of evidence).`
      );
      setDiscoveryDone(true);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setBusy(false);
    }
  }

  const wavesByNumber = waves.reduce<Record<number, string[]>>((acc, w) => {
    (acc[w.wave_number] ||= []).push(w.entity_id);
    return acc;
  }, {});
  const hasWaves = Object.keys(wavesByNumber).length > 0;

  const step1Done = loaded;
  const step2Done = artifacts.length > 0 || hasWaves;
  const step3Done = discoveryDone || hasWaves;
  const step4Done = false;

  return (
    <div className="app-shell">
      <NavBar />

      <div className="progress-stepper">
        <ProgressStep index={1} label="Load project" active={!step1Done} done={step1Done} />
        <div className={`progress-connector ${step1Done ? "done" : ""}`} />
        <ProgressStep index={2} label="Upload artifacts" active={step1Done && !step2Done} done={step2Done} />
        <div className={`progress-connector ${step2Done ? "done" : ""}`} />
        <ProgressStep index={3} label="Run discovery" active={step2Done && !step3Done} done={step3Done} />
        <div className={`progress-connector ${step3Done ? "done" : ""}`} />
        <ProgressStep index={4} label="Verify a wave" active={step3Done} done={step4Done} />
      </div>

      <div className="card">
        <h2>
          <span className="section-icon">1️⃣</span>Load a project
        </h2>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Type a project / scenario ID. Try a pre-loaded demo scenario, or any ID of your own to
          start a fresh project.
        </p>
        <input value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="Project / scenario ID" />
        <button onClick={() => refresh()} disabled={busy}>
          🔍 Load project
        </button>
        <div style={{ marginTop: 14 }}>
          {DEMO_SCENARIOS.map((id) => (
            <button key={id} className="chip" onClick={() => { setProjectId(id); refresh(id); }}>
              {id}
            </button>
          ))}
        </div>
      </div>

      {loaded && (
        <>
          <div className="card">
            <h2>
              <span className="section-icon">2️⃣</span>Upload artifacts <span style={{ color: "var(--muted)", fontWeight: 400, fontSize: 13 }}>(optional)</span>
            </h2>
            <p style={{ color: "var(--muted)", fontSize: 13 }}>
              Only needed to test live AI extraction on your own data. Pre-loaded demo scenarios
              already have data ready — skip to step 4.
            </p>
            <input type="file" onChange={handleUpload} disabled={busy} />
            <p style={{ color: "var(--muted)", fontSize: 12 }}>
              Accepted: vm_inventory.csv, dns_records.csv, network_connections.csv,
              application_config.json, architecture.md, service_catalog.csv, migration_plan.json
            </p>

            <h3 style={{ marginTop: 20, fontSize: 14 }}>Existing artifacts ({artifacts.length})</h3>
            {artifacts.length === 0 && <p style={{ color: "var(--muted)" }}>No artifacts uploaded yet.</p>}
            {artifacts.map((uri) => {
              const filename = filenameFromUri(uri);
              return (
                <div className="file-row" key={uri}>
                  <span className="file-row-name">
                    <span>{fileIcon(filename)}</span>
                    {filename}
                  </span>
                  <button className="icon-btn" title="Delete" onClick={() => handleDeleteArtifact(uri)} disabled={busy}>
                    🗑
                  </button>
                </div>
              );
            })}
            {artifacts.length > 0 && (
              <button className="danger" style={{ marginTop: 10 }} onClick={handleDeleteAll} disabled={busy}>
                🗑 Delete all artifacts
              </button>
            )}
          </div>

          <div className="card">
            <h2>
              <span className="section-icon">3️⃣</span>Run discovery <span style={{ color: "var(--muted)", fontWeight: 400, fontSize: 13 }}>(optional)</span>
            </h2>
            <p style={{ color: "var(--muted)" }}>
              Runs the Gemini + ADK Discovery and Evidence agents against uploaded artifacts,
              extracting entities and evidence-backed dependencies into BigQuery.
            </p>
            <button onClick={handleRunDiscovery} disabled={busy || artifacts.length === 0}>
              ▶ Run discovery
            </button>
            {artifacts.length === 0 && (
              <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 8 }}>
                Upload at least one artifact first, or skip this for pre-loaded demo scenarios.
              </p>
            )}
          </div>

          <div className="card">
            <h2>
              <span className="section-icon">4️⃣</span>Migration plan — verify a wave
            </h2>
            {!hasWaves && <p style={{ color: "var(--muted)" }}>No waves loaded yet for this project.</p>}
            <div className="wave-timeline">
              {Object.entries(wavesByNumber)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([waveNumber, entityIds]) => (
                  <div className="wave-node" key={waveNumber}>
                    <div className="wave-node-line" />
                    <div className="wave-node-circle">{waveNumber}</div>
                    <div className="wave-node-body">
                      <strong>Wave {waveNumber}</strong>
                      <div style={{ margin: "8px 0" }}>
                        {entityIds.map((eid) => (
                          <span className="badge type-service" key={eid}>
                            {eid}
                          </span>
                        ))}
                      </div>
                      <button onClick={() => navigate(`/result?project=${projectId}&wave=${waveNumber}`)}>
                        ✓ Verify Wave {waveNumber}
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </>
      )}

      {status && <p className="status-text">{status}</p>}
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
