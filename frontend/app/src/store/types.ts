export type StaffStatus = "active" | "draft" | "inactive";

export interface CrudItem {
  id: string;
  name: string;
  desc: string;
  enabled: boolean;
}

export interface SubAgent {
  id: string;
  name: string;
  desc: string;
}

export interface StaffConfig {
  prompt: string;
  rules: string;
  memory: string;
  tools: CrudItem[];
  mcps: CrudItem[];
  skills: CrudItem[];
  subAgents: SubAgent[];
}

export interface Staff {
  id: string;
  name: string;
  role: string;
  description: string;
  status: StaffStatus;
  version: string;
  config: StaffConfig;
  created_at: number;
  updated_at: number;
}

export type TaskStatus = "pending" | "running" | "completed" | "failed";
export type Priority = "high" | "medium" | "low";

export interface Task {
  id: string;
  title: string;
  description: string;
  assignee_id: string;
  status: TaskStatus;
  priority: Priority;
  progress: number;
  deadline: string;
  created_at: number;
}

export interface ResourceItem {
  id: string;
  name: string;
  desc: string;
  category: string;
  type: string;
  created_at: number;
  updated_at: number;
}

export interface UserProfile {
  name: string;
  initials: string;
  email: string;
}
