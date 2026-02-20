import { useCallback, useEffect, useState } from "react";
import {
  getQueueMode,
  setQueueMode,
  steerThread,
  type ChatEntry,
} from "../api";

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface AppActionsDeps {
  activeThreadId: string | null;
  setEntries: React.Dispatch<React.SetStateAction<ChatEntry[]>>;
}

export interface AppActionsState {
  queueEnabled: boolean;
  computerOpen: boolean;
  computerTab: "terminal" | "files" | "agents";
  focusedAgentStepId: string | null;
  sidebarCollapsed: boolean;
  searchOpen: boolean;
  sessionsOpen: boolean;
  newThreadOpen: boolean;
}

export interface AppActionsSetters {
  setComputerOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setComputerTab: (tab: "terminal" | "files" | "agents") => void;
  setFocusedAgentStepId: (id: string | null) => void;
  setSidebarCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  setSearchOpen: (open: boolean) => void;
  setSessionsOpen: (open: boolean) => void;
  setNewThreadOpen: (open: boolean) => void;
}

export interface AppActionsHandlers {
  handleFocusAgent: (stepId: string) => void;
  handleSendQueueMessage: (message: string) => Promise<void>;
  handleToggleQueue: () => Promise<void>;
}

export function useAppActions(deps: AppActionsDeps): AppActionsState & AppActionsSetters & AppActionsHandlers {
  const { activeThreadId, setEntries } = deps;

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [computerOpen, setComputerOpen] = useState(false);
  const [computerTab, setComputerTab] = useState<"terminal" | "files" | "agents">("terminal");
  const [focusedAgentStepId, setFocusedAgentStepId] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sessionsOpen, setSessionsOpen] = useState(false);
  const [newThreadOpen, setNewThreadOpen] = useState(false);
  const [queueEnabled, setQueueEnabled] = useState(false);

  // Load queue mode from backend on mount
  useEffect(() => {
    if (!activeThreadId) return;
    getQueueMode(activeThreadId)
      .then((r) => setQueueEnabled(r.mode !== "steer"))
      .catch(() => {});
  }, [activeThreadId]);

  const handleFocusAgent = useCallback((stepId: string) => {
    setFocusedAgentStepId(stepId);
    setComputerTab("agents");
    setComputerOpen(true);
  }, []);

  const handleSendQueueMessage = useCallback(
    async (message: string) => {
      if (!activeThreadId) return;
      const userEntry: ChatEntry = { id: makeId("user"), role: "user", content: message, timestamp: Date.now() };
      setEntries((prev) => [...prev, userEntry]);
      await steerThread(activeThreadId, message);
    },
    [activeThreadId, setEntries],
  );

  const handleToggleQueue = useCallback(async () => {
    const next = !queueEnabled;
    setQueueEnabled(next);
    if (activeThreadId) {
      try {
        await setQueueMode(activeThreadId, next ? "followup" : "steer");
      } catch {
        // ignore -- backend may not support this yet
      }
    }
  }, [activeThreadId, queueEnabled]);

  return {
    queueEnabled, computerOpen, computerTab, focusedAgentStepId,
    sidebarCollapsed, searchOpen, sessionsOpen, newThreadOpen,
    setComputerOpen, setComputerTab, setFocusedAgentStepId,
    setSidebarCollapsed, setSearchOpen, setSessionsOpen, setNewThreadOpen,
    handleFocusAgent, handleSendQueueMessage, handleToggleQueue,
  };
}
