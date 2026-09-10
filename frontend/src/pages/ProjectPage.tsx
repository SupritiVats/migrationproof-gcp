import { useState } from "react";
import { useNavigate } from "react-router-dom";
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

export default function ProjectPage() {
  const navigate = useNavigate();
  const [projectId, setProjectId] = useState("scn-02-db-migrated-after-app");
  const [loaded, setLoaded] = useState(false);
  const [artifacts, setArtifacts] = useState<string[]>([]);
  const [waves, setWaves] = useState<{ entity_id: string; wave_number: number }[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setError(null);
    try {
      const [artifactsResult, wavesResult] = await Promise.all([
        listArtifacts(projectId),
        listWaves(projectId),
      ]);
      setArtifacts(artifactsResult.artifacts);
      setWaves(wavesResult.waves);
      setLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    }
  }

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

  return (
    <div className="app-shell">
      <NavBar />

      <div className="card">
        <h2>1. Load a project</h2>
        <p style={{ color: "#8b98a5", fontSize: 13 }}>
          Type a project / scenario ID. Try a pre-loaded demo scenario, or any ID of your own to
          start a fresh project.
        </p>
        <input value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="Project / scenario ID" />
        <button onClick={refresh} disabled={busy}>
          Load project
        </button>
        <div style={{ marginTop: 12 }}>
          {DEMO_SCENARIOS.map((id) => (
            <button
              key={id}
              className="secondary"
              style={{ marginRight: 6, marginBottom: 6, fontSize: 12, padding: "6px 10px" }}
              onClick={() => setProjectId(id)}
            >
              {id}
            </button>
          ))}
        </div>
      </div>

      {loaded && (
        <>
          <div className="card">
            <h2>2. Upload artifacts (optional)</h2>
            <p style={{ color: "#8b98a5", fontSize: 13 }}>
              Only needed if you want to test live AI extraction on your own data. Pre-loaded demo
              scenarios already have their data ready — skip to step 4.
            </p>
            <input type="file" onChange={handleUpload} disabled={busy} />
            <p style={{ color: "#8b98a5", fontSize: 12 }}>
              Accepted: vm_inventory.csv, dns_records.csv, network_connections.csv,
              application_config.json, architecture.md, service_catalog.csv, migration_plan.json
            </p>

            <h3 style={{ marginTop: 20 }}>Existing artifacts ({artifacts.length})</h3>
            {artifacts.length === 0 && <p style={{ color: "#8b98a5" }}>No artifacts uploaded yet.</p>}
            <ul style={{ listStyle: "none", padding: 0 }}>
              {artifacts.map((uri) => (
                <li
                  key={uri}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontFamily: "monospace",
                    fontSize: 12,
                    padding: "6px 0",
                    borderBottom: "1px solid #202b36",
                  }}
                >
                  <span>{filenameFromUri(uri)}</span>
                  <button
                    className="secondary"
                    style={{ fontSize: 12, padding: "4px 10px", color: "#f87171" }}
                    onClick={() => handleDeleteArtifact(uri)}
                    disabled={busy}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
            {artifacts.length > 0 && (
              <button className="secondary" style={{ marginTop: 12, color: "#f87171" }} onClick={handleDeleteAll} disabled={busy}>
                Delete all artifacts
              </button>
            )}
          </div>

          <div className="card">
            <h2>3. Run discovery (optional)</h2>
            <p style={{ color: "#8b98a5" }}>
              Runs the Gemini + ADK Discovery and Evidence agents against the uploaded artifacts,
              extracting entities and evidence-backed dependencies into BigQuery.
            </p>
            <button onClick={handleRunDiscovery} disabled={busy || artifacts.length === 0}>
              Run discovery
            </button>
            {artifacts.length === 0 && (
              <p style={{ color: "#8b98a5", fontSize: 12, marginTop: 8 }}>
                Upload at least one artifact first, or skip this for pre-loaded demo scenarios.
              </p>
            )}
          </div>

          <div className="card">
            <h2>4. Migration plan / waves — verify a wave</h2>
            {Object.keys(wavesByNumber).length === 0 && (
              <p style={{ color: "#8b98a5" }}>No waves loaded yet for this project.</p>
            )}
            {Object.entries(wavesByNumber)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([waveNumber, entityIds]) => (
                <div key={waveNumber} style={{ marginBottom: 16 }}>
                  <strong>Wave {waveNumber}</strong>
                  <div style={{ margin: "6px 0" }}>
                    {entityIds.map((eid) => (
                      <span className="badge" key={eid}>
                        {eid}
                      </span>
                    ))}
                  </div>
                  <button onClick={() => navigate(`/result?project=${projectId}&wave=${waveNumber}`)}>
                    Verify Wave {waveNumber}
                  </button>
                </div>
              ))}
          </div>
        </>
      )}

      {status && <p style={{ color: "#8b98a5" }}>{status}</p>}
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
