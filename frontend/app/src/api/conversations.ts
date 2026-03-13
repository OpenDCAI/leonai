import { authRequest } from "../store/auth-store";

export interface ConversationSummary {
  id: string;
  agent_member_id: string;
  title: string;
  status: string;
  created_at: number;
  members: string[];
}

export async function createConversation(
  agentMemberId: string,
  title?: string,
): Promise<ConversationSummary> {
  return authRequest<ConversationSummary>("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ agent_member_id: agentMemberId, title }),
  });
}

export async function listConversations(): Promise<ConversationSummary[]> {
  return authRequest<ConversationSummary[]>("/api/conversations");
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  created_at: number;
}

export async function listMessages(
  conversationId: string,
  limit = 50,
): Promise<ConversationMessage[]> {
  return authRequest<ConversationMessage[]>(
    `/api/conversations/${encodeURIComponent(conversationId)}/messages?limit=${limit}`,
  );
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await authRequest(`/api/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
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
