import { Folder, Send } from "lucide-react";
import { useState } from "react";
import type { SandboxType } from "../api";
import { Button } from "./ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover";
import { Input } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import FilesystemBrowser from "./FilesystemBrowser";

interface CenteredInputBoxProps {
  sandboxTypes: SandboxType[];
  defaultSandbox?: string;
  defaultWorkspace?: string;
  defaultModel?: string;
  recentWorkspaces?: string[];
  onSend: (message: string, sandbox: string, model: string, workspace?: string) => Promise<void>;
}

const MODELS = [
  { value: "leon:mini", label: "Mini" },
  { value: "leon:medium", label: "Medium" },
  { value: "leon:large", label: "Large" },
  { value: "leon:max", label: "Max" },
];

export default function CenteredInputBox({
  sandboxTypes,
  defaultSandbox = "local",
  defaultWorkspace,
  defaultModel = "leon:medium",
  recentWorkspaces = [],
  onSend,
}: CenteredInputBoxProps) {
  const [message, setMessage] = useState("");
  const [sandbox, setSandbox] = useState(defaultSandbox);
  const [model, setModel] = useState(defaultModel);
  const [workspace, setWorkspace] = useState(defaultWorkspace || "");
  const [customWorkspace, setCustomWorkspace] = useState("");
  const [sending, setSending] = useState(false);
  const [workspacePopoverOpen, setWorkspacePopoverOpen] = useState(false);

  const isLocalSandbox = sandbox === "local";

  async function handleSend() {
    const text = message.trim();
    if (!text || sending) return;

    setSending(true);
    try {
      const finalWorkspace = customWorkspace || workspace || undefined;
      await onSend(text, sandbox, model, finalWorkspace);
      setMessage("");
      setCustomWorkspace("");
    } finally {
      setSending(false);
    }
  }

  function handleSelectWorkspace(path: string) {
    setWorkspace(path);
    setCustomWorkspace("");
  }

  function handleBrowserSelect(path: string) {
    setWorkspace(path);
    setCustomWorkspace("");
    setWorkspacePopoverOpen(false);
  }

  function handleCustomWorkspace() {
    if (customWorkspace.trim()) {
      setWorkspace(customWorkspace.trim());
      setWorkspacePopoverOpen(false);
    }
  }

  // ============================================================
  // IMPORTANT: DO NOT remove or truncate the return statement below!
  // This component must return complete JSX with proper closing tags.
  // ====================================================
  return (
    <div className="w-[600px]">
      <div className="bg-[#fafafa] rounded-[24px] border border-[#e5e5e5] shadow-lg p-6">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
          placeholder="告诉 Leon 你需要什么帮助..."
          className="w-full bg-transparent text-base resize-none outline-none border-none text-[#171717] placeholder:text-[#a3a3a3] mb-4"
          rows={6}
          disabled={sending}
          style={{ boxShadow: "none" }}
        />

        <div className="flex items-center gap-2">
          <Select value={sandbox} onValueChange={setSandbox}>
            <SelectTrigger className="w-[140px] h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sandboxTypes.map((type) => (
                <SelectItem key={type.name} value={type.name} disabled={!type.available}>
                  {type.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {isLocalSandbox && (
            <Popover open={workspacePopoverOpen} onOpenChange={setWorkspacePopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-9 w-9"
                  title={workspace || "选择工作区"}
                >
                  <Folder className="h-4 w-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[480px]" align="start">
                <Tabs defaultValue="browse" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="browse">浏览</TabsTrigger>
                    <TabsTrigger value="recent">最近</TabsTrigger>
                    <TabsTrigger value="manual">手动</TabsTrigger>
                  </TabsList>

                  <TabsContent value="browse" className="space-y-3 mt-3">
                    <FilesystemBrowser
                      onSelect={handleBrowserSelect}
                      initialPath={workspace || "~"}
                    />
                  </TabsContent>

                  <TabsContent value="recent" className="space-y-3 mt-3">
                    {workspace && (
                      <div className="text-xs text-muted-foreground mb-2">
                        当前: {workspace}
                      </div>
                    )}
                    {recentWorkspaces.length > 0 ? (
                      <div className="space-y-1">
                        {recentWorkspaces.map((path) => (
                          <button
                            key={path}
                            onClick={() => handleSelectWorkspace(path)}
                            className="w-full text-left px-2 py-1.5 text-sm hover:bg-accent rounded-md truncate"
                          >
                            {path}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground text-center py-4">
                        暂无最近使用的工作区
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="manual" className="space-y-3 mt-3">
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">自定义路径</p>
                      <div className="flex gap-2">
                        <Input
                          value={customWorkspace}
                          onChange={(e) => setCustomWorkspace(e.target.value)}
                          placeholder="例如: ~/Projects"
                          className="flex-1 h-8 text-sm"
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              handleCustomWorkspace();
                            }
                          }}
                        />
                        <Button
                          size="sm"
                          onClick={handleCustomWorkspace}
                          disabled={!customWorkspace.trim()}
                        >
                          确定
                        </Button>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </PopoverContent>
            </Popover>
          )}

          <Select value={model} onValueChange={setModel}>
            <SelectTrigger className="w-[160px] h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODELS.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex-1" />

          <Button
            onClick={() => void handleSend()}
            disabled={!message.trim() || sending}
            className="h-9 px-4 bg-[#171717] text-white hover:bg-[#404040] rounded-lg"
          >
            <Send className="w-4 h-4 mr-2" />
            发送
          </Button>
        </div>
      </div>
    </div>
  );
  // ============================================================
  // END OF COMPONENT - All JSX tags properly closed above
  // ============================================================
}
