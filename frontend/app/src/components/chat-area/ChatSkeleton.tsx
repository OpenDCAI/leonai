import { Skeleton } from "../ui/skeleton";

export function ChatSkeleton() {
  return (
    <div className="max-w-3xl mx-auto px-5 space-y-3.5 py-5 animate-fade-in">
      {/* Simulated user message */}
      <div className="flex justify-end">
        <Skeleton className="h-9 w-[45%] rounded-xl" />
      </div>
      {/* Simulated assistant response */}
      <div className="flex gap-2.5">
        <Skeleton className="w-6 h-6 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3.5 w-[20%]" />
          <Skeleton className="h-3.5 w-[90%]" />
          <Skeleton className="h-3.5 w-[75%]" />
          <Skeleton className="h-3.5 w-[60%]" />
        </div>
      </div>
      {/* Simulated user message */}
      <div className="flex justify-end">
        <Skeleton className="h-9 w-[35%] rounded-xl" />
      </div>
      {/* Simulated assistant response */}
      <div className="flex gap-2.5">
        <Skeleton className="w-6 h-6 rounded-full flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3.5 w-[15%]" />
          <Skeleton className="h-3.5 w-[85%]" />
          <Skeleton className="h-3.5 w-[50%]" />
        </div>
      </div>
    </div>
  );
}
