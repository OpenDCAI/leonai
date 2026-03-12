import { authRequest } from "../store/auth-store";

export interface ConversationSummary {
  id: string;
  agent_member_id: string;
  title: string;
  status: string;
  created_at: number;
  members: string[];
}

export async function listConversations(): Promise<ConversationSummary[]> {
  return authRequest<ConversationSummary[]>("/api/conversations");
}

export async function sendConversationMessage(
  conversationId: string,
  content: string,
): Promise<Record<string, unknown>> {
  return authRequest(`/api/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}
