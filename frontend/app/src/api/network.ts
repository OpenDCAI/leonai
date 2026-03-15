import { authRequest } from "../store/auth-store";
import type { MemberInfo } from "./conversations";

export type GraphNode = MemberInfo;

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export async function fetchGraph(): Promise<GraphData> {
  return authRequest<GraphData>("/api/network/graph");
}
