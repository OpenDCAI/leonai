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

