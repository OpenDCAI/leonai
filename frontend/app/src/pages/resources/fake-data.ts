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
    telemetry: {
      running: { used: 2, limit: null, unit: "sandbox", source: "derived" },
      cpu: { used: 1.9, limit: null, unit: "cores", source: "derived" },
      memory: { used: 3.2, limit: null, unit: "GB", source: "derived" },
      disk: { used: 41.7, limit: null, unit: "GB", source: "derived" },
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
    id: "daytona-cloud",
    name: "Daytona Cloud",
    description: "Managed cloud sandboxes",
    vendor: "Daytona",
    type: "cloud",
    status: "ready",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: true,
      screenshot: false,
      web: false,
      process: false,
      hooks: true,
      snapshot: false,
    },
    telemetry: {
      running: { used: 3, limit: 20, unit: "sandbox", source: "api" },
      cpu: { used: 6, limit: null, unit: "cores", source: "derived" },
      memory: { used: 12, limit: null, unit: "GB", source: "derived" },
      disk: { used: 80, limit: null, unit: "GB", source: "derived" },
    },
    consoleUrl: "https://app.daytona.io",
    sessions: [],
  },
  {
    id: "daytona-selfhost",
    name: "Daytona Self-Host",
    description: "Private Daytona deployment",
    vendor: "Daytona",
    type: "container",
    status: "active",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: true,
      screenshot: false,
      web: false,
      process: true,
      hooks: true,
      snapshot: false,
    },
    telemetry: {
      running: { used: 4, limit: 12, unit: "sandbox", source: "api" },
      cpu: { used: 9.5, limit: 16, unit: "cores", source: "api" },
      memory: { used: 20.5, limit: 64, unit: "GB", source: "api" },
      disk: { used: 130, limit: 512, unit: "GB", source: "api" },
    },
    consoleUrl: "https://daytona.f2j.space",
    sessions: [
      {
        id: "sess-ds01",
        threadId: "thread-101",
        agentId: "coder",
        agentName: "Coder",
        status: "running",
        startedAt: "6 分钟前",
      },
      {
        id: "sess-ds02",
        threadId: "thread-102",
        agentId: "researcher",
        agentName: "Researcher",
        status: "running",
        startedAt: "11 分钟前",
      },
    ],
  },
  {
    id: "e2b",
    name: "E2B",
    description: "Cloud sandbox with runtime metrics",
    vendor: "E2B",
    type: "cloud",
    status: "active",
    capabilities: {
      filesystem: true,
      terminal: true,
      metrics: true,
      screenshot: false,
      web: false,
      process: false,
      hooks: false,
      snapshot: true,
    },
    telemetry: {
      running: { used: 3, limit: 20, unit: "sandbox", source: "api" },
      cpu: { used: 2.8, limit: 20, unit: "cores", source: "api" },
      memory: { used: 6.4, limit: 80, unit: "GB", source: "api" },
      disk: { used: 14.2, limit: 200, unit: "GB", source: "api" },
      quota: { used: 680, limit: 1000, unit: "credits", source: "plan" },
    },
    quota: { used: 680, limit: 1000 },
    latencyMs: 45,
    consoleUrl: "https://e2b.dev/docs",
    sessions: [
      {
        id: "sess-e2b-01",
        threadId: "thread-211",
        agentId: "default",
        agentName: "Default",
        status: "running",
        startedAt: "3 分钟前",
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
    telemetry: {
      running: { used: 2, limit: 8, unit: "sandbox", source: "api" },
      cpu: { used: null, limit: null, unit: "cores", source: "unknown" },
      memory: { used: null, limit: null, unit: "GB", source: "unknown" },
      disk: { used: null, limit: null, unit: "GB", source: "unknown" },
      quota: { used: 230, limit: 1000, unit: "points", source: "console" },
    },
    quota: { used: 230, limit: 1000 },
    latencyMs: 12,
    consoleUrl: "https://agentbay.console.aliyun.com/overview",
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
      process: true,
      hooks: false,
      snapshot: false,
    },
    telemetry: {
      running: { used: 0, limit: 10, unit: "container", source: "api" },
      cpu: { used: 0, limit: 8, unit: "cores", source: "api" },
      memory: { used: 0, limit: 32, unit: "GB", source: "api" },
      disk: { used: 0, limit: 256, unit: "GB", source: "api" },
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
