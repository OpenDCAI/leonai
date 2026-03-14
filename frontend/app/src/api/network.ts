import { authRequest } from "../store/auth-store";

export interface GraphNode {
  id: string;
  name: string;
  type: string;
}

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
