export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    credentials: "include",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText}: ${text || "<no body>"}`);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function getOverview() {
  return await http<any>("/api/operator/dashboards/overview");
}

export async function search(q: string) {
  const u = new URL("/api/operator/search", window.location.origin);
  u.searchParams.set("q", q);
  return await http<any>(u.pathname + u.search);
}

export async function listSandboxes(status?: string) {
  const u = new URL("/api/operator/sandboxes", window.location.origin);
  if (status) u.searchParams.set("status", status);
  return await http<any>(u.pathname + u.search);
}

export async function listThreadRuns(threadId: string) {
  return await http<any>(`/api/threads/${encodeURIComponent(threadId)}/runs`);
}

export async function getRun(runId: string) {
  return await http<any>(`/api/runs/${encodeURIComponent(runId)}`);
}

export async function getRunEvents(runId: string, afterId?: number) {
  const u = new URL(`/api/runs/${encodeURIComponent(runId)}/events`, window.location.origin);
  if (afterId !== undefined) u.searchParams.set("after_id", String(afterId));
  return await http<any>(u.pathname + u.search);
}

export async function getThreadDiagnostics(threadId: string) {
  return await http<any>(`/api/operator/threads/${encodeURIComponent(threadId)}/diagnostics`);
}

export async function getThreadCommands(threadId: string) {
  return await http<any>(`/api/operator/threads/${encodeURIComponent(threadId)}/commands`);
}

export async function getProviderEvents(threadId?: string, provider?: string) {
  const u = new URL("/api/operator/provider-events", window.location.origin);
  if (threadId) u.searchParams.set("thread_id", threadId);
  if (provider) u.searchParams.set("provider", provider);
  return await http<any>(u.pathname + u.search);
}

export async function getOrphans() {
  return await http<any>("/api/operator/orphans");
}

export async function adoptOrphan(instanceId: string, provider: string, threadId: string) {
  return await http<any>(`/api/operator/orphans/${encodeURIComponent(instanceId)}/adopt?provider=${encodeURIComponent(provider)}&thread_id=${encodeURIComponent(threadId)}`, { method: "POST" });
}

export async function destroyOrphan(instanceId: string, provider: string) {
  return await http<any>(`/api/operator/orphans/${encodeURIComponent(instanceId)}/destroy?provider=${encodeURIComponent(provider)}`, { method: "POST" });
}

export async function pauseSession(threadId: string) {
  return await http<any>(`/api/operator/sessions/${encodeURIComponent(threadId)}/pause`, { method: "POST" });
}

export async function resumeSession(threadId: string) {
  return await http<any>(`/api/operator/sessions/${encodeURIComponent(threadId)}/resume`, { method: "POST" });
}

export async function destroySession(threadId: string) {
  return await http<any>(`/api/operator/sessions/${encodeURIComponent(threadId)}/destroy`, { method: "POST" });
}

