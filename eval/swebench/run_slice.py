"""Run a small SWE-bench slice with LeonAgent and evaluate via official harness."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from datasets import load_dataset
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from swebench.harness.constants import KEY_INSTANCE_ID, KEY_MODEL, KEY_PREDICTION

from agent import LeonAgent
from sandbox.thread_context import set_current_thread_id


def run(cmd: list[str], cwd: Path | None = None, timeout_sec: int | None = None) -> str:
    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"command timeout after {timeout_sec}s\ncmd={' '.join(cmd)}"
        ) from exc
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed rc={proc.returncode}\ncmd={' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc.stdout


def _has_commit(repo_dir: Path, commit: str) -> bool:
    env = dict(os.environ)
    env.setdefault("GIT_NO_LAZY_FETCH", "1")
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "cat-file", "-e", f"{commit}^{{commit}}"],
        text=True,
        capture_output=True,
        env=env,
    )
    return proc.returncode == 0


def ensure_repo_cache(repo: str, base_commit: str, cache_root: Path, git_timeout_sec: int) -> Path:
    repo_dir = cache_root / repo.replace("/", "__")
    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        # @@@repo-cache-partial-clone - use blobless clone for faster first-time cache warmup on large repos.
        run(
            ["git", "clone", "--filter=blob:none", "--no-checkout", f"https://github.com/{repo}.git", str(repo_dir)],
            timeout_sec=git_timeout_sec,
        )
    if not _has_commit(repo_dir, base_commit):
        # @@@fetch-target-commit-only - fetch only missing target commit to avoid expensive full remote fetch on every instance.
        run(
            ["git", "-C", str(repo_dir), "fetch", "--no-tags", "origin", base_commit, "--depth=1"],
            timeout_sec=git_timeout_sec,
        )
    return repo_dir


def parse_tests(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    raise ValueError(f"unsupported tests payload: {type(raw)}")


def build_prompt(row: dict[str, Any], prompt_profile: str) -> str:
    fail_tests = parse_tests(row.get("FAIL_TO_PASS"))
    pass_tests = parse_tests(row.get("PASS_TO_PASS"))
    pass_preview = pass_tests[:20]
    prompt = [
        "You are solving one SWE-bench task in the current repository.",
        "",
        "Rules:",
        "1. Make the minimal code change required by the issue.",
        "2. Run focused tests before finishing.",
        "3. Do not touch unrelated files.",
        "",
        f"Instance: {row['instance_id']}",
        f"Repo: {row['repo']}",
        "",
        "Issue statement:",
        str(row["problem_statement"]).strip(),
        "",
        "Hints:",
        str(row.get("hints_text", "")).strip() or "(none)",
        "",
        "Tests that should pass after your fix:",
        *[f"- {t}" for t in fail_tests],
    ]
    if pass_preview:
        prompt.extend(["", "Regression tests to keep passing (preview):", *[f"- {t}" for t in pass_preview]])
    if prompt_profile == "heuristic":
        prompt.extend(
            [
                "",
                "Execution constraints (strict):",
                "- Use tool name `run_command` instead of `bash`.",
                "- Use `python3` instead of `python` in commands.",
                "- Keep a tight budget: at most 12 tool calls total for this task.",
                "- Stop early once you have enough evidence for a minimal fix; do not continue exploring.",
                "- If the same command pattern fails twice without new information, stop tool use.",
                "- If key tests pass OR you cannot make further progress with high confidence, stop tool use immediately.",
                "- Final turn must be plain text only: provide (1) files changed, (2) why the fix works, (3) tests run + results, (4) remaining risks.",
                "- After the final summary, do not call any tools.",
            ]
        )
    prompt.extend(
        [
            "",
            "At the end, summarize what you changed and why.",
        ]
    )
    return "\n".join(prompt)


def build_thread_id(thread_prefix: str, run_stamp: str, instance_id: str) -> str:
    safe_stamp = re.sub(r"[^a-zA-Z0-9_.-]+", "-", run_stamp)
    return f"{thread_prefix}-{safe_stamp}-{instance_id}"


def snapshot_sqlite_db(source_db: Path, snapshot_db: Path) -> None:
    if not source_db.exists():
        raise RuntimeError(f"source trace db not found: {source_db}")
    snapshot_db.parent.mkdir(parents=True, exist_ok=True)
    if snapshot_db.exists():
        snapshot_db.unlink()
    src = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    dst = sqlite3.connect(str(snapshot_db))
    try:
        # @@@trace-db-isolation - copy shared trace DB to run-local snapshot so reporting never holds locks on the live DB.
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _msg_text(msg: Any) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
        return "".join(texts)
    return str(content)


def collect_trace_summary(thread_id: str, instance_id: str, db_path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "select checkpoint, metadata from checkpoints where thread_id=? order by rowid",
            (thread_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "instance_id": instance_id,
            "thread_id": thread_id,
            "checkpoint_count": 0,
            "message_count": 0,
            "human_messages": 0,
            "ai_messages": 0,
            "tool_messages": 0,
            "tool_calls_total": 0,
            "tool_call_counter": {},
            "error_markers": {},
        }

    serde = JsonPlusSerializer()
    checkpoint_blob, metadata_blob = rows[-1]
    checkpoint = serde.loads_typed(("msgpack", checkpoint_blob))
    metadata = json.loads(metadata_blob.decode())
    messages = checkpoint.get("channel_values", {}).get("messages", [])

    tool_calls: list[str] = []
    error_markers = Counter()
    human_messages = 0
    ai_messages = 0
    tool_messages = 0
    for msg in messages:
        cls = msg.__class__.__name__
        if cls == "HumanMessage":
            human_messages += 1
        elif cls == "AIMessage":
            ai_messages += 1
            for call in getattr(msg, "tool_calls", None) or []:
                tool_calls.append(str(call.get("name", "<unknown>")))
        elif cls == "ToolMessage":
            tool_messages += 1
            text = _msg_text(msg).lower()
            if text.startswith("error: bash is not a valid tool"):
                error_markers["invalid_tool_bash"] += 1
            if "recursion limit of" in text:
                error_markers["recursion_limit"] += 1
            if "command failed rc=" in text:
                error_markers["command_failed"] += 1
            if "command 'python' not found" in text:
                error_markers["python_not_found"] += 1

    return {
        "instance_id": instance_id,
        "thread_id": thread_id,
        "checkpoint_count": len(rows),
        "last_step": metadata.get("step"),
        "message_count": len(messages),
        "human_messages": human_messages,
        "ai_messages": ai_messages,
        "tool_messages": tool_messages,
        "tool_calls_total": len(tool_calls),
        "tool_call_counter": dict(Counter(tool_calls)),
        "error_markers": dict(error_markers),
        "last_ai_message": _msg_text(next((m for m in reversed(messages) if m.__class__.__name__ == "AIMessage"), ""))[
            :300
        ].replace("\n", " "),
    }


async def run_instance(
    row: dict[str, Any],
    repo_cache_root: Path,
    workspaces_root: Path,
    timeout_sec: int,
    git_timeout_sec: int,
    recursion_limit: int,
    keep_worktree: bool,
    thread_id: str,
    prompt_profile: str,
    model_name: str,
) -> dict[str, Any]:
    instance_id = row["instance_id"]
    repo = row["repo"]
    base_commit = row["base_commit"]
    print(f"[slice] start {instance_id} repo={repo} commit={base_commit}")

    repo_cache = ensure_repo_cache(repo, base_commit, repo_cache_root, git_timeout_sec=git_timeout_sec)
    workspace = workspaces_root / instance_id
    run(["git", "-C", str(repo_cache), "worktree", "prune"], timeout_sec=git_timeout_sec)
    if workspace.exists():
        try:
            run(["git", "-C", str(repo_cache), "worktree", "remove", "--force", str(workspace)], timeout_sec=git_timeout_sec)
        except Exception:
            shutil.rmtree(workspace)

    # @@@git-worktree-lifecycle - worktree gives clean per-instance state without recloning full repo each run.
    run(["git", "-C", str(repo_cache), "worktree", "add", "--detach", str(workspace), base_commit], timeout_sec=git_timeout_sec)
    agent: LeonAgent | None = None
    try:
        prompt = build_prompt(row, prompt_profile=prompt_profile)
        agent = LeonAgent(workspace_root=workspace, model_name=model_name)
        if getattr(agent, "_needs_async_init", False):
            await agent.ainit()
        set_current_thread_id(thread_id)
        await asyncio.wait_for(
            agent.agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config={"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit},
            ),
            timeout=timeout_sec,
        )
        patch = run(["git", "-C", str(workspace), "diff"], timeout_sec=120)
        if not patch.strip():
            print(f"[slice] warning empty patch for {instance_id}")
        return {
            KEY_INSTANCE_ID: instance_id,
            KEY_MODEL: "leonai-main",
            KEY_PREDICTION: patch,
        }
    finally:
        # @@@agent-explicit-close - do deterministic cleanup to avoid lingering threads/processes after each instance.
        if agent is not None:
            agent.close()
        set_current_thread_id("")
        if keep_worktree:
            print(f"[slice] keep workspace {workspace}")
        else:
            try:
                run(
                    ["git", "-C", str(repo_cache), "worktree", "remove", "--force", "--force", str(workspace)],
                    timeout_sec=git_timeout_sec,
                )
            except Exception as cleanup_exc:
                # @@@worktree-cleanup-fallback - don't mask the real task error with cleanup failures.
                print(f"[slice] cleanup_warning {instance_id}: {cleanup_exc}")
                shutil.rmtree(workspace, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a small SWE-bench slice with LeonAgent")
    p.add_argument("--dataset", default="SWE-bench/SWE-bench_Lite")
    p.add_argument("--split", default="test")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--timeout-sec", type=int, default=900)
    p.add_argument("--git-timeout-sec", type=int, default=240)
    p.add_argument("--recursion-limit", type=int, default=60)
    p.add_argument("--eval-timeout-sec", type=int, default=1800)
    p.add_argument("--output-dir", default="artifacts/swebench")
    p.add_argument("--keep-worktree", action="store_true")
    p.add_argument("--run-id", default="")
    p.add_argument("--arm", default="A")
    p.add_argument("--model-name", default="")
    p.add_argument("--prompt-profile", choices=["baseline", "heuristic"], default="baseline")
    p.add_argument("--thread-prefix", default="swebench")
    p.add_argument("--source-trace-db", default=str(Path.home() / ".leon" / "leon.db"))
    p.add_argument("--trace-db", default="")
    p.add_argument("--no-eval", action="store_true")
    return p.parse_args()


async def amain() -> None:
    args = parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required")

    output_dir = Path(args.output_dir).resolve()
    cache_root = output_dir / "repo_cache"
    workspaces_root = output_dir / "workspaces"
    run_stamp = args.run_id or datetime.now(timezone.utc).strftime("slice-%Y%m%d-%H%M%S")
    run_dir = output_dir / run_stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    source_trace_db = Path(args.source_trace_db).expanduser().resolve()
    if not source_trace_db.exists():
        raise RuntimeError(f"source trace db not found: {source_trace_db}")
    if args.trace_db:
        trace_db = Path(args.trace_db).expanduser().resolve()
    else:
        trace_db = run_dir / "trace_snapshot.db"

    print(
        f"[slice] run_id={run_stamp} arm={args.arm} prompt_profile={args.prompt_profile} "
        f"dataset={args.dataset} split={args.split} start={args.start} count={args.count} "
        f"model_name={args.model_name or '(active)'}"
    )
    ds = load_dataset(args.dataset, split=args.split)
    rows = [ds[i] for i in range(args.start, args.start + args.count)]

    predictions: list[dict[str, Any]] = []
    trace_summaries: list[dict[str, Any]] = []
    trace_targets: list[dict[str, str]] = []
    instance_ids: list[str] = []
    errors: list[dict[str, str]] = []
    for row in rows:
        instance_id = str(row["instance_id"])
        thread_id = build_thread_id(args.thread_prefix, run_stamp, instance_id)
        try:
            pred = await run_instance(
                row=row,
                repo_cache_root=cache_root,
                workspaces_root=workspaces_root,
                timeout_sec=args.timeout_sec,
                git_timeout_sec=args.git_timeout_sec,
                recursion_limit=args.recursion_limit,
                keep_worktree=args.keep_worktree,
                thread_id=thread_id,
                prompt_profile=args.prompt_profile,
                model_name=args.model_name,
            )
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            tb = traceback.format_exc()
            # @@@slice-error-traceback - print full traceback so run failures can be attributed without guesswork.
            print(f"[slice] error {instance_id}: {msg}\n{tb}")
            errors.append({"instance_id": instance_id, "thread_id": thread_id, "error": msg, "traceback": tb})
            pred = {
                KEY_INSTANCE_ID: instance_id,
                KEY_MODEL: "leonai-main",
                KEY_PREDICTION: "",
            }
        predictions.append(pred)
        instance_ids.append(str(pred[KEY_INSTANCE_ID]))
        trace_targets.append({"instance_id": instance_id, "thread_id": thread_id})
        print(f"[slice] done {pred[KEY_INSTANCE_ID]} patch_len={len(pred[KEY_PREDICTION])}")

    # @@@trace-snapshot-once - snapshot the shared trace DB once per run to avoid O(N) full-file copies for multi-instance slices.
    if trace_targets:
        snapshot_sqlite_db(source_db=source_trace_db, snapshot_db=trace_db)
        for target in trace_targets:
            summary = collect_trace_summary(
                thread_id=target["thread_id"],
                instance_id=target["instance_id"],
                db_path=trace_db,
            )
            trace_summaries.append(summary)
            print(f"[slice] trace {target['instance_id']} checkpoints={summary.get('checkpoint_count', 0)}")

    predictions_path = run_dir / "predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as f:
        for item in predictions:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    ids_path = run_dir / "instance_ids.txt"
    ids_path.write_text("\n".join(instance_ids) + "\n", encoding="utf-8")
    trace_path = run_dir / "trace_summaries.jsonl"
    with trace_path.open("w", encoding="utf-8") as f:
        for item in trace_summaries:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[slice] predictions={predictions_path}")
    print(f"[slice] instance_ids={ids_path}")
    print(f"[slice] trace_summaries={trace_path}")
    if errors:
        errors_path = run_dir / "errors.json"
        errors_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[slice] errors={errors_path}")

    eval_summary_path = ""
    eval_error = ""
    if not args.no_eval:
        # @@@swebench-eval-contract - pass explicit instance ids so harness evaluates only this small slice.
        eval_cmd = [
            sys.executable,
            "-m",
            "swebench.harness.run_evaluation",
            "--dataset_name",
            args.dataset,
            "--split",
            args.split,
            "--predictions_path",
            str(predictions_path),
            "--instance_ids",
            *instance_ids,
            "--max_workers",
            "1",
            "--run_id",
            run_stamp,
            "--report_dir",
            str(run_dir),
        ]
        print(f"[slice] eval_cmd={' '.join(eval_cmd)}")
        try:
            # @@@harness-timeout - fail loud on harness hangs instead of blocking the whole run indefinitely.
            run(eval_cmd, timeout_sec=args.eval_timeout_sec)
            print(f"[slice] evaluation complete run_dir={run_dir}")
            candidate = Path.cwd() / f"leonai-main.{run_stamp}.json"
            if candidate.exists():
                eval_summary_path = str(candidate)
                print(f"[slice] eval_summary={candidate}")
        except Exception as exc:
            eval_error = str(exc)
            print(f"[slice] evaluation_error={eval_error}")
    else:
        print("[slice] skip evaluation (--no-eval)")

    manifest = {
        "run_id": run_stamp,
        "arm": args.arm,
        "model_name": args.model_name,
        "prompt_profile": args.prompt_profile,
        "dataset": args.dataset,
        "split": args.split,
        "start": args.start,
        "count": args.count,
        "timeout_sec": args.timeout_sec,
        "git_timeout_sec": args.git_timeout_sec,
        "recursion_limit": args.recursion_limit,
        "thread_prefix": args.thread_prefix,
        "source_trace_db": str(source_trace_db),
        "trace_db": str(trace_db),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "instances_total": len(instance_ids),
        "errors_total": len(errors),
        "empty_patch_total": sum(1 for p in predictions if not p[KEY_PREDICTION].strip()),
        "predictions_path": str(predictions_path),
        "instance_ids_path": str(ids_path),
        "trace_summaries_path": str(trace_path),
        "eval_summary_path": eval_summary_path,
        "eval_error": eval_error,
    }
    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[slice] manifest={manifest_path}")
    if eval_error:
        raise RuntimeError(f"evaluation failed after manifest write: {eval_error}")


if __name__ == "__main__":
    asyncio.run(amain())
