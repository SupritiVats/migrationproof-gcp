const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";
const TOKEN_KEY = "migrationproof_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function login(username: string, password: string) {
  return request<{ token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function uploadArtifact(projectId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<{ project_id: string; filename: string; gcs_uri: string }>(
    `/artifacts/upload/${projectId}`,
    { method: "POST", body: form }
  );
}

export function listArtifacts(projectId: string) {
  return request<{ project_id: string; artifacts: string[] }>(`/artifacts/${projectId}`);
}

export function deleteArtifact(projectId: string, filename: string) {
  return request<{ deleted: boolean }>(`/artifacts/${projectId}/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
}

export function deleteAllArtifacts(projectId: string) {
  return request<{ deleted_count: number }>(`/artifacts/${projectId}`, { method: "DELETE" });
}

export function runDiscovery(projectId: string) {
  return request<Record<string, unknown>>(`/discovery/run/${projectId}`, { method: "POST" });
}

export function listWaves(projectId: string) {
  return request<{ waves: { entity_id: string; wave_number: number }[] }>(`/waves/${projectId}`);
}

export interface VerificationReason {
  rule: string;
  message: string;
  related_entity_ids: string[];
  related_dependency_ids: string[];
}

export interface VerificationResult {
  result_id: string;
  scenario_id: string;
  wave_number: number;
  decision: "ALLOW" | "BLOCK";
  reasons: VerificationReason[];
  confidence: number;
  blast_radius: Record<string, string[]>;
  narrative: string | null;
}

export function verify(projectId: string, targetWave: number) {
  return request<VerificationResult>("/verify", {
    method: "POST",
    body: JSON.stringify({ project_id: projectId, target_wave: targetWave }),
  });
}
