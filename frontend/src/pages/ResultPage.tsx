import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { verify, VerificationResult } from "../api/client";
import NavBar from "../components/NavBar";

export default function ResultPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const projectId = params.get("project") || "";
  const wave = Number(params.get("wave") || "1");

  const [result, setResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    verify(projectId, wave)
      .then((r) => !cancelled && setResult(r))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Verification failed"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [projectId, wave]);

  return (
    <div className="app-shell">
      <NavBar />

      <button className="secondary" onClick={() => navigate("/project")} style={{ marginBottom: 16 }}>
        ← Back to project
      </button>

      <div className="card">
        <h2>
          Verifying {projectId} — Wave {wave}
        </h2>

        {loading && <p>Running verification engine...</p>}
        {error && <p className="error-text">{error}</p>}

        {result && (
          <>
            <div className={`decision-banner ${result.decision === "ALLOW" ? "allow" : "block"}`}>
              {result.decision === "ALLOW" ? "🟢 SAFE TO MIGRATE" : "🔴 MIGRATION BLOCKED"}
            </div>

            <p>
              <strong>Confidence:</strong> {(result.confidence * 100).toFixed(0)}%
            </p>

            {result.narrative && (
              <div className="card" style={{ background: "#0b0f14" }}>
                <h3>Explanation</h3>
                <p>{result.narrative}</p>
              </div>
            )}

            <h3>Reasons</h3>
            {result.reasons.length === 0 && <p style={{ color: "#8b98a5" }}>No blocking or advisory conditions found.</p>}
            {result.reasons.map((reason, i) => (
              <div className="reason-item" key={i}>
                <div className="badge">{reason.rule}</div>
                <p style={{ margin: "6px 0 0" }}>{reason.message}</p>
              </div>
            ))}

            {result.blast_radius && Object.keys(result.blast_radius).length > 0 && (
              <>
                <h3 style={{ marginTop: 20 }}>Predicted blast radius</h3>
                <p style={{ color: "#8b98a5", fontSize: 13 }}>
                  If an entity below is disrupted by this migration, these downstream services would
                  be affected too.
                </p>
                {Object.entries(result.blast_radius).map(([entity, affected]) => (
                  <div key={entity} className="card" style={{ background: "#0b0f14", padding: 14, marginBottom: 8 }}>
                    <strong>{entity}</strong>
                    <div style={{ marginTop: 6 }}>
                      {affected.length === 0 ? (
                        <span style={{ color: "#8b98a5", fontSize: 13 }}>No downstream dependents.</span>
                      ) : (
                        affected.map((eid) => (
                          <span className="badge" key={eid}>
                            {eid}
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
