import type { AllocatedResource, ProviderInfo, ResourceType } from "./types";

export const PROVIDER_REGISTRY: ProviderInfo[] = [
  {
    id: "local",
    name: "Local",
    description: "Direct host access · Always available",
    type: "local",
    status: "active",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: false,
      screenshot: false,
      web: false,
      process: false,
      hooks: false,
      snapshot: false,
    },
    sessions: [
      {
        id: "sess-lo01",
        threadId: "thread-001",
        agentId: "default",
        agentName: "Default",
        status: "running",
        startedAt: "2 分钟前",
      },
      {
        id: "sess-lo02",
        threadId: "thread-003",
        agentId: "coder",
        agentName: "Coder",
        status: "running",
        startedAt: "8 分钟前",
      },
      {
        id: "sess-lo03",
        threadId: "thread-005",
        agentId: "default",
        agentName: "Default",
        status: "paused",
        startedAt: "25 分钟前",
      },
    ],
  },
  {
    id: "agentbay",
    name: "AgentBay",
    description: "Remote Linux sandbox (Ubuntu)",
    vendor: "Alibaba Cloud",
    type: "cloud",
    status: "active",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: true,
      screenshot: true,
      web: true,
      process: true,
      hooks: false,
      snapshot: false,
    },
    quota: { used: 230, limit: 1000 },
    latencyMs: 12,
    sessions: [
      {
        id: "sess-a1b2",
        threadId: "thread-001",
        agentId: "coder",
        agentName: "Coder",
        status: "running",
        startedAt: "2 分钟前",
        metrics: {
          cpu: 23,
          memory: 25,
          disk: 12,
          networkIn: 45.3,
          networkOut: 12.1,
          webUrl: "https://sandbox-abc123.agentbay.cloud",
        },
      },
      {
        id: "sess-f6e5",
        threadId: "thread-002",
        agentId: "researcher",
        agentName: "Researcher",
        status: "paused",
        startedAt: "15 分钟前",
        metrics: {
          cpu: 2,
          memory: 18,
          disk: 8,
          networkIn: 0,
          networkOut: 0,
        },
      },
    ],
  },
  {
    id: "docker",
    name: "Docker",
    description: "Isolated container sandbox",
    type: "container",
    status: "unavailable",
    unavailableReason: "Docker 未安装或未运行",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: true,
      screenshot: false,
      web: false,
      process: false,
      hooks: false,
      snapshot: false,
    },
    sessions: [],
  },
  {
    id: "e2b",
    name: "E2B",
    description: "Cloud sandbox with snapshot support",
    vendor: "E2B",
    type: "cloud",
    status: "ready",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: false,
      screenshot: false,
      web: false,
      process: false,
      hooks: false,
      snapshot: true,
    },
    quota: { used: 680, limit: 1000 },
    latencyMs: 45,
    sessions: [],
  },
  {
    id: "daytona",
    name: "Daytona",
    description: "Development environment sandbox",
    vendor: "Daytona",
    type: "cloud",
    status: "ready",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: false,
      screenshot: false,
      web: false,
      process: false,
      hooks: true,
      snapshot: false,
    },
    sessions: [],
  },
];

export const CAPABILITY_LABELS: Record<string, string> = {
  filesystem: "文件",
  terminal: "终端",
  metrics: "指标",
  screenshot: "截屏",
  web: "Web",
  process: "进程",
  hooks: "Hook",
  snapshot: "快照",
};

export const CAPABILITY_KEYS = [
  "filesystem",
  "terminal",
  "metrics",
  "screenshot",
  "web",
  "process",
  "hooks",
  "snapshot",
] as const;

/** Derive allocated resources from provider registry: each session gets one resource per enabled capability */
export function deriveAllocatedResources(providers: ProviderInfo[]): AllocatedResource[] {
  const resources: AllocatedResource[] = [];
  for (const provider of providers) {
    for (const session of provider.sessions) {
      for (const key of CAPABILITY_KEYS) {
        if (provider.capabilities[key]) {
          resources.push({
            resourceType: key as ResourceType,
            providerId: provider.id,
            providerName: provider.name,
            agentId: session.agentId,
            agentName: session.agentName,
            sessionId: session.id,
            sessionStatus: session.status,
          });
        }
      }
    }
  }
  return resources;
}
