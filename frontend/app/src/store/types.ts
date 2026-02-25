export type MemberStatus = "active" | "draft" | "inactive";

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

export interface MemberConfig {
  prompt: string;
  rules: string;
  memory: string;
  tools: CrudItem[];
  mcps: CrudItem[];
  skills: CrudItem[];
  subAgents: SubAgent[];
}

export interface Member {
  id: string;
  name: string;
  description: string;
  status: MemberStatus;
  version: string;
  config: MemberConfig;
  created_at: number;
  updated_at: number;
  builtin?: boolean;
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

// Backward compatibility aliases
export type StaffStatus = MemberStatus;
export type StaffConfig = MemberConfig;
export type Staff = Member;
