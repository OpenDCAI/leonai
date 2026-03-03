import type { ProviderInfo } from "./types";

interface ResourceOverviewResponse {
  providers: ProviderInfo[];
}

export async function fetchResourceProviders(): Promise<ProviderInfo[]> {
  const response = await fetch("/api/monitor/resources", {
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }

  const payload = (await response.json()) as ResourceOverviewResponse;
  if (!payload || !Array.isArray(payload.providers)) {
    throw new Error("Unexpected /api/monitor/resources response shape");
  }
  return payload.providers;
}
