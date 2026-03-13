import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./ui/dialog";
import { useAuthStore } from "@/store/auth-store";
import { createConversation } from "@/api/conversations";

interface NewChatDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConversationCreated?: () => Promise<void>;
}

export default function NewChatDialog({ open, onOpenChange, onConversationCreated }: NewChatDialogProps) {
  const navigate = useNavigate();
  const agent = useAuthStore(s => s.agent);
  const [creating, setCreating] = useState(false);

  const handleSelect = async () => {
    if (!agent || creating) return;
    setCreating(true);
    try {
      const conv = await createConversation(agent.id);
      onOpenChange(false);
      await onConversationCreated?.();
      navigate(`/chat/leon/${conv.id}`);
    } catch (err) {
      console.error("[NewChatDialog] Failed to create conversation:", err);
    } finally {
      setCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md p-0 gap-0">
        <DialogHeader className="px-4 pt-4 pb-3">
          <DialogTitle className="text-base">发起会话</DialogTitle>
          <DialogDescription className="sr-only">选择成员发起新对话</DialogDescription>
        </DialogHeader>
        <div className="border-t max-h-80 overflow-y-auto">
          {!agent ? (
            <p className="text-sm text-muted-foreground text-center py-8">暂无可用成员</p>
          ) : (
            <button
              onClick={() => void handleSelect()}
              disabled={creating}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted transition-colors disabled:opacity-50"
            >
              <div className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-medium shrink-0">
                {agent.name.slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{agent.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">在线</span>
                </div>
                <p className="text-xs text-muted-foreground truncate mt-0.5">Your AI assistant</p>
              </div>
              <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
            </button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
