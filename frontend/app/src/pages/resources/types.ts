export type ProviderStatus = "active" | "ready" | "unavailable";

export type ProviderType = "local" | "cloud" | "container";

export interface ProviderCapabilities {
  filesystem: boolean;
  terminal: boolean;
  metrics: boolean;
  screenshot: boolean;
  web: boolean;
  process: boolean;
  hooks: boolean;
  snapshot: boolean;
}

export interface ProviderQuota {
  used: number;
  limit: number;
}

export interface SessionMetrics {
  cpu: number;
  memory: number;
  disk: number;
  networkIn: number;
  networkOut: number;
  webUrl?: string;
}

export interface ResourceSession {
  id: string;
  threadId: string;
  agentId: string;
  agentName: string;
  status: "running" | "paused" | "stopped";
  startedAt: string;
  metrics?: SessionMetrics;
}

export interface ProviderInfo {
  id: string;
  name: string;
  description: string;
  vendor?: string;
  type: ProviderType;
  status: ProviderStatus;
  unavailableReason?: string;
  capabilities: ProviderCapabilities;
  quota?: ProviderQuota;
  latencyMs?: number;
  sessions: ResourceSession[];
}

/** An atomic resource allocated to an agent via a provider session */
export type ResourceType = keyof ProviderCapabilities;

export interface AllocatedResource {
  resourceType: ResourceType;
  providerId: string;
  providerName: string;
  agentId: string;
  agentName: string;
  sessionId: string;
  sessionStatus: ResourceSession["status"];
}
