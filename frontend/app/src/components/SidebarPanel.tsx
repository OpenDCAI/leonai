/**
 * SidebarPanel — shared sidebar frame for Threads and Chats.
 * Provides: header (title + action) + search + scrollable item list.
 * Items rendered via render prop for maximum flexibility.
 */

import { Search, Plus } from "lucide-react";
import { useState } from "react";

interface SidebarPanelProps {
  title: string;
  /** Search placeholder text */
  searchPlaceholder?: string;
  /** Called when "+" button is clicked */
  onAdd?: () => void;
  /** Current search query (controlled) */
  searchQuery?: string;
  /** Search query change handler (controlled) */
  onSearchChange?: (query: string) => void;
  /** Item count badge next to title */
  count?: number;
  /** Width in pixels */
  width?: number;
  /** Loading state */
  loading?: boolean;
  /** Empty state content */
  emptyContent?: React.ReactNode;
  /** List items */
  children: React.ReactNode;
}

export default function SidebarPanel({
  title,
  searchPlaceholder = "Search...",
  onAdd,
  searchQuery: controlledQuery,
  onSearchChange,
  count,
  width = 288,
  loading,
  emptyContent,
  children,
}: SidebarPanelProps) {
  const [localQuery, setLocalQuery] = useState("");
  const query = controlledQuery ?? localQuery;
  const setQuery = onSearchChange ?? setLocalQuery;

  return (
    <div className="h-full flex flex-col bg-card border-r border-border shrink-0" style={{ width }}>
      {/* Header */}
      <div className="px-4 pt-3 pb-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{title}</span>
          {count !== undefined && (
            <span className="text-[11px] text-muted-foreground/40">{count}</span>
          )}
        </div>
        {onAdd && (
          <button
            onClick={onAdd}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Search */}
      <div className="px-3 pb-3">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground/60 hover:bg-muted/30 focus-within:bg-muted/30 border border-transparent focus-within:border-primary/40 transition-colors">
          <Search className="w-4 h-4 shrink-0" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="flex-1 bg-transparent outline-none text-foreground placeholder:text-muted-foreground/60 text-sm"
          />
        </div>
      </div>

      <div className="h-px mx-3 bg-border" />

      {/* Scrollable list */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-xs text-muted-foreground">Loading...</p>
          </div>
        ) : emptyContent ? (
          emptyContent
        ) : (
          children
        )}
      </div>
    </div>
  );
}
