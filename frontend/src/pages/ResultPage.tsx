import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { verify, VerificationResult } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function ResultPage() {
  const { logout } = useAuth();
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
      <div className="top-nav">
        <h1>🔒 MigrationProof</h1>
        <button className="secondary" onClick={logout}>
          Sign out
        </button>
      </div>

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
          </>
        )}
      </div>
    </div>
  );
}
