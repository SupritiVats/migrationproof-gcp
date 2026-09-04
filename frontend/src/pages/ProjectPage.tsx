import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { listArtifacts, listWaves, runDiscovery, uploadArtifact } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function ProjectPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [projectId, setProjectId] = useState("scn-02-db-migrated-after-app");
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
      setStatus(`Uploaded ${file.name}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRunDiscovery() {
    setBusy(true);
    setError(null);
    try {
      const result = await runDiscovery(projectId);
      setStatus(`Discovery complete: ${JSON.stringify(result)}`);
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
      <div className="top-nav">
        <h1>🔒 MigrationProof</h1>
        <button className="secondary" onClick={logout}>
          Sign out
        </button>
      </div>

      <div className="card">
        <h2>Project</h2>
        <input value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="Project / scenario ID" />
        <button onClick={refresh} disabled={busy}>
          Load project
        </button>
      </div>

      <div className="card">
        <h2>Upload artifacts</h2>
        <input type="file" onChange={handleUpload} disabled={busy} />
        <p style={{ color: "#8b98a5", fontSize: 13 }}>
          vm_inventory.csv, dns_records.csv, network_connections.csv, application_config.json,
          architecture.md, service_catalog.csv, migration_plan.json
        </p>
        <h3 style={{ marginTop: 20 }}>Existing artifacts</h3>
        <ul>
          {artifacts.map((uri) => (
            <li key={uri} style={{ fontFamily: "monospace", fontSize: 13 }}>
              {uri}
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h2>Discovery</h2>
        <p style={{ color: "#8b98a5" }}>
          Runs the Gemini + ADK Discovery and Evidence agents against the uploaded artifacts.
        </p>
        <button onClick={handleRunDiscovery} disabled={busy}>
          Run discovery
        </button>
      </div>

      <div className="card">
        <h2>Migration plan / waves</h2>
        {Object.keys(wavesByNumber).length === 0 && <p style={{ color: "#8b98a5" }}>No waves loaded yet.</p>}
        {Object.entries(wavesByNumber)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([waveNumber, entityIds]) => (
            <div key={waveNumber} style={{ marginBottom: 12 }}>
              <strong>Wave {waveNumber}</strong>
              <div>
                {entityIds.map((eid) => (
                  <span className="badge" key={eid}>
                    {eid}
                  </span>
                ))}
              </div>
              <button
                className="secondary"
                style={{ marginTop: 8 }}
                onClick={() => navigate(`/result?project=${projectId}&wave=${waveNumber}`)}
              >
                Verify Wave {waveNumber}
              </button>
            </div>
          ))}
      </div>

      {status && <p style={{ color: "#8b98a5" }}>{status}</p>}
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
