import { ChevronRight, Folder, Home } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";

interface DirectoryItem {
  name: string;
  path: string;
  is_dir: boolean;
}

interface FilesystemBrowserProps {
  onSelect: (path: string) => void;
  initialPath?: string;
}

export default function FilesystemBrowser({
  onSelect,
  initialPath = "~",
}: FilesystemBrowserProps) {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [items, setItems] = useState<DirectoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadDirectory(path: string) {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `http://127.0.0.1:8001/api/settings/browse?path=${encodeURIComponent(path)}`
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "加载失败");
      }

      const data = await response.json();
      setCurrentPath(data.current_path);
      setParentPath(data.parent_path);
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDirectory(initialPath);
  }, [initialPath]);

  function handleNavigate(path: string) {
    void loadDirectory(path);
  }

  function handleSelect() {
    onSelect(currentPath);
  }

  return (
    <div className="space-y-3">
      {/* Current Path */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleNavigate("~")}
          title="返回主目录"
        >
          <Home className="h-3.5 w-3.5" />
        </Button>
        <div className="flex-1 text-sm text-muted-foreground truncate">
          {currentPath}
        </div>
      </div>

      {/* Parent Directory */}
      {parentPath && (
        <button
          onClick={() => handleNavigate(parentPath)}
          className="w-full flex items-center gap-2 px-2 py-1.5 text-sm hover:bg-accent rounded-md"
        >
          <Folder className="h-4 w-4 text-muted-foreground" />
          <span>..</span>
        </button>
      )}

      {/* Directory List */}
      <ScrollArea className="h-[300px] border rounded-md">
        <div className="p-2 space-y-1">
          {loading && (
            <div className="text-sm text-muted-foreground text-center py-4">
              加载中...
            </div>
          )}

          {error && (
            <div className="text-sm text-red-500 text-center py-4">{error}</div>
          )}

          {!loading && !error && items.length === 0 && (
            <div className="text-sm text-muted-foreground text-center py-4">
              此目录为空
            </div>
          )}

          {!loading &&
            !error &&
            items.map((item) => (
              <button
                key={item.path}
                onClick={() => handleNavigate(item.path)}
                className="w-full flex items-center gap-2 px-2 py-1.5 text-sm hover:bg-accent rounded-md"
              >
                <Folder className="h-4 w-4 text-muted-foreground" />
                <span className="flex-1 text-left truncate">{item.name}</span>
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            ))}
        </div>
      </ScrollArea>

      {/* Select Button */}
      <Button onClick={handleSelect} className="w-full" disabled={loading}>
        选择此目录
      </Button>
    </div>
  );
}
