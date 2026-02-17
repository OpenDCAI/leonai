import { useEffect, useState } from "react";

export interface UserSettings {
  default_workspace: string | null;
  recent_workspaces: string[];
  default_model: string;
  active_model: string | null;
  enabled_models: string[];
}

export function useWorkspaceSettings() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadSettings() {
    try {
      const response = await fetch("http://127.0.0.1:8001/api/settings");
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  }

  async function setDefaultWorkspace(workspace: string): Promise<void> {
    const response = await fetch("http://127.0.0.1:8001/api/settings/workspace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace }),
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Failed to set workspace");
    }

    await loadSettings();
  }

  async function addRecentWorkspace(workspace: string): Promise<void> {
    try {
      await fetch("http://127.0.0.1:8001/api/settings/workspace/recent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace }),
      });
      await loadSettings();
    } catch (err) {
      console.error("Failed to add recent workspace:", err);
    }
  }

  useEffect(() => {
    void loadSettings();
  }, []);

  return {
    settings,
    loading,
    setDefaultWorkspace,
    addRecentWorkspace,
    refreshSettings: loadSettings,
    hasWorkspace: settings?.default_workspace != null,
  };
}
