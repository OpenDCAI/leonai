"""Metrics collector for eval trajectories.

Tier 1 (SystemMetrics): token/cost/context aggregation
Tier 2 (ObjectiveMetrics): per-tool timing, LLM latency, efficiency
"""

from __future__ import annotations

from eval.models import (
    ObjectiveMetrics,
    RunTrajectory,
    SystemMetrics,
    ToolTimingStats,
)


def _percentile(sorted_values: list[float], p: float) -> float:
    """Calculate p-th percentile from pre-sorted values."""
    if not sorted_values:
        return 0.0
    idx = int(p * (len(sorted_values) - 1))
    return sorted_values[idx]


class MetricsCollector:
    """Compute Tier 1 and Tier 2 metrics from a RunTrajectory."""

    def compute_system_metrics(
        self,
        trajectory: RunTrajectory,
        runtime_status: dict | None = None,
    ) -> SystemMetrics:
        """Tier 1: aggregate token, cost, and context metrics."""
        total_tokens = sum(c.total_tokens for c in trajectory.llm_calls)
        input_tokens = sum(c.input_tokens for c in trajectory.llm_calls)
        output_tokens = sum(c.output_tokens for c in trajectory.llm_calls)
        cache_read = sum(c.cache_read_tokens for c in trajectory.llm_calls)
        cache_write = sum(c.cache_write_tokens for c in trajectory.llm_calls)
        total_cost = sum(c.cost_usd for c in trajectory.llm_calls)

        denominator = input_tokens + cache_read + cache_write
        cache_hit_rate = cache_read / denominator if denominator > 0 else 0.0

        context_usage_percent = 0.0
        if runtime_status:
            ctx = runtime_status.get("context", {})
            context_usage_percent = ctx.get("usage_percent", 0.0)

        return SystemMetrics(
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            cache_hit_rate=cache_hit_rate,
            context_usage_percent=context_usage_percent,
            message_count=len(trajectory.llm_calls) + len(trajectory.tool_calls),
            llm_call_count=len(trajectory.llm_calls),
            tool_call_count=len(trajectory.tool_calls),
            total_cost_usd=total_cost,
        )

    def compute_objective_metrics(self, trajectory: RunTrajectory) -> ObjectiveMetrics:
        """Tier 2: per-tool timing, LLM latency, efficiency metrics."""
        # --- Per-tool timing stats ---
        tool_groups: dict[str, list] = {}
        for tc in trajectory.tool_calls:
            tool_groups.setdefault(tc.tool_name, []).append(tc)

        tool_timing_stats: dict[str, ToolTimingStats] = {}
        slow_operations: list[str] = []

        for name, calls in tool_groups.items():
            durations = sorted(c.duration_ms for c in calls)
            successes = sum(1 for c in calls if c.success)
            count = len(calls)
            avg_ms = sum(durations) / count if count else 0.0
            max_ms = durations[-1] if durations else 0.0
            p95_ms = _percentile(durations, 0.95)
            success_rate = successes / count if count else 1.0

            tool_timing_stats[name] = ToolTimingStats(
                tool_name=name,
                count=count,
                avg_ms=avg_ms,
                max_ms=max_ms,
                p95_ms=p95_ms,
                success_rate=success_rate,
            )

            # Detect slow operations
            slow_threshold = 60000.0 if name in ("read_file", "readFile") else 30000.0
            for c in calls:
                if c.duration_ms > slow_threshold:
                    slow_operations.append(f"{name}:{c.tool_call_id} ({c.duration_ms:.0f}ms)")

        # --- LLM latency ---
        llm_durations = sorted(c.duration_ms for c in trajectory.llm_calls)
        llm_avg = sum(llm_durations) / len(llm_durations) if llm_durations else 0.0
        llm_max = llm_durations[-1] if llm_durations else 0.0
        llm_p95 = _percentile(llm_durations, 0.95)

        # --- Duration and efficiency ---
        total_duration_ms = 0.0
        if trajectory.started_at and trajectory.finished_at:
            from datetime import datetime

            try:
                start = datetime.fromisoformat(trajectory.started_at)
                end = datetime.fromisoformat(trajectory.finished_at)
                total_duration_ms = (end - start).total_seconds() * 1000
            except (ValueError, TypeError):
                pass

        total_tokens = sum(c.total_tokens for c in trajectory.llm_calls)
        tokens_per_second = total_tokens / (total_duration_ms / 1000) if total_duration_ms > 0 else 0.0

        llm_count = len(trajectory.llm_calls)
        tool_calls_per_llm = len(trajectory.tool_calls) / llm_count if llm_count > 0 else 0.0

        return ObjectiveMetrics(
            tool_timing_stats=tool_timing_stats,
            llm_latency_avg_ms=llm_avg,
            llm_latency_max_ms=llm_max,
            llm_latency_p95_ms=llm_p95,
            total_duration_ms=total_duration_ms,
            tokens_per_second=tokens_per_second,
            tool_calls_per_llm_call=tool_calls_per_llm,
            slow_operations=slow_operations,
        )

    def compute_all(
        self,
        trajectory: RunTrajectory,
        runtime_status: dict | None = None,
    ) -> tuple[SystemMetrics, ObjectiveMetrics]:
        """Compute both Tier 1 and Tier 2 metrics."""
        return (
            self.compute_system_metrics(trajectory, runtime_status),
            self.compute_objective_metrics(trajectory),
        )
