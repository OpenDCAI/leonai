"""Time travel manager for checkpoint navigation and file rollback"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from langgraph.checkpoint.sqlite import SqliteSaver

from tui.operations import FileOperation, FileOperationRecorder, get_recorder

if TYPE_CHECKING:
    pass


@dataclass
class CheckpointInfo:
    """Information about a checkpoint"""

    checkpoint_id: str
    thread_id: str
    timestamp: datetime
    user_message: str | None  # First user message in this checkpoint
    file_operations_count: int
    is_current: bool = False


@dataclass
class RewindResult:
    """Result of a rewind operation"""

    success: bool
    message: str
    reverted_operations: list[FileOperation]
    errors: list[str]


class TimeTravelManager:
    """Manages time travel (checkpoint navigation and file rollback)"""

    def __init__(
        self,
        checkpointer: SqliteSaver | None = None,
        recorder: FileOperationRecorder | None = None,
    ):
        # Always create our own sync SqliteSaver for reading checkpoints
        # This works regardless of whether the agent uses sync or async checkpointer
        db_path = Path.home() / ".leon" / "leon.db"
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.checkpointer = SqliteSaver(self._conn)
        self.recorder = recorder or get_recorder()

    def get_checkpoints(self, thread_id: str, user_turns_only: bool = False) -> list[CheckpointInfo]:
        """Get all checkpoints for a thread with metadata

        Args:
            thread_id: The thread ID to get checkpoints for
            user_turns_only: If True, only return checkpoints where a new user message was added
        """
        checkpoints = []
        config = {"configurable": {"thread_id": thread_id}}
        last_user_message = None  # Track last seen user message

        try:
            # Get state history from LangGraph (newest first)
            history = list(self.checkpointer.list(config))

            for i, checkpoint_tuple in enumerate(history):
                checkpoint = checkpoint_tuple.checkpoint
                checkpoint_id = checkpoint_tuple.config["configurable"].get("checkpoint_id", "")

                # Extract timestamp
                ts = checkpoint_tuple.metadata.get("created_at") if checkpoint_tuple.metadata else None
                if ts:
                    if isinstance(ts, str):
                        timestamp = datetime.fromisoformat(ts)
                    else:
                        timestamp = datetime.fromtimestamp(ts)
                else:
                    timestamp = datetime.now()

                # Extract user message from checkpoint state
                user_message = None
                if checkpoint and "channel_values" in checkpoint:
                    messages = checkpoint["channel_values"].get("messages", [])
                    # Find the last human message
                    for msg in reversed(messages):
                        if hasattr(msg, "__class__") and msg.__class__.__name__ == "HumanMessage":
                            content = msg.content
                            if isinstance(content, str):
                                user_message = content[:100] + "..." if len(content) > 100 else content
                            break

                # Count file operations for this checkpoint
                file_ops_count = self.recorder.count_operations_for_checkpoint(thread_id, checkpoint_id)

                checkpoints.append(
                    CheckpointInfo(
                        checkpoint_id=checkpoint_id,
                        thread_id=thread_id,
                        timestamp=timestamp,
                        user_message=user_message,
                        file_operations_count=file_ops_count,
                        is_current=(i == 0),  # First in history is current
                    )
                )

            # Reverse to show oldest first
            checkpoints.reverse()
            if checkpoints:
                checkpoints[-1].is_current = True

            # Filter to only user turns if requested
            if user_turns_only and checkpoints:
                filtered = []
                last_msg = None
                for cp in checkpoints:
                    if cp.user_message != last_msg:
                        filtered.append(cp)
                        last_msg = cp.user_message
                # Ensure current marker is on the last one
                if filtered:
                    for cp in filtered:
                        cp.is_current = False
                    filtered[-1].is_current = True
                checkpoints = filtered

        except Exception as e:
            print(f"[TimeTravelManager] Error getting checkpoints: {e}")

        return checkpoints

    def get_operations_to_revert(self, thread_id: str, target_checkpoint_id: str) -> list[FileOperation]:
        """Get list of operations that would be reverted when rewinding to target"""
        checkpoints = self.get_checkpoints(thread_id)

        # Find target checkpoint index
        target_idx = None
        for i, cp in enumerate(checkpoints):
            if cp.checkpoint_id == target_checkpoint_id:
                target_idx = i
                break

        if target_idx is None:
            return []

        # Collect all operations from checkpoints after target
        operations_to_revert = []
        for cp in checkpoints[target_idx + 1 :]:
            ops = self.recorder.get_operations_for_checkpoint(thread_id, cp.checkpoint_id)
            operations_to_revert.extend(ops)

        # Return in reverse order (newest first) for proper rollback
        operations_to_revert.reverse()
        return operations_to_revert

    def rewind_to(self, thread_id: str, target_checkpoint_id: str) -> RewindResult:
        """Rewind to a specific checkpoint, reverting file operations"""
        operations_to_revert = self.get_operations_to_revert(thread_id, target_checkpoint_id)

        reverted = []
        errors = []

        # Revert operations in reverse order (newest first)
        for op in operations_to_revert:
            try:
                self._revert_operation(op)
                reverted.append(op)
            except Exception as e:
                errors.append(f"Failed to revert {op.file_path}: {e}")

        # Mark operations as reverted in database
        if reverted:
            self.recorder.mark_reverted([op.id for op in reverted])

        # Delete checkpoints after target from LangGraph database
        try:
            self._delete_checkpoints_after(thread_id, target_checkpoint_id)
        except Exception as e:
            errors.append(f"Failed to delete checkpoints: {e}")

        success = len(errors) == 0
        if success:
            message = f"Successfully reverted {len(reverted)} file operations"
        else:
            message = f"Reverted {len(reverted)} operations with {len(errors)} errors"

        return RewindResult(
            success=success,
            message=message,
            reverted_operations=reverted,
            errors=errors,
        )

    def _delete_checkpoints_after(self, thread_id: str, target_checkpoint_id: str) -> None:
        """Delete all checkpoints after the target checkpoint"""
        # Get all checkpoints (oldest first)
        checkpoints = self.get_checkpoints(thread_id, user_turns_only=False)

        # Find target index
        target_idx = None
        for i, cp in enumerate(checkpoints):
            if cp.checkpoint_id == target_checkpoint_id:
                target_idx = i
                break

        if target_idx is None:
            return

        # Get checkpoint IDs to delete (all after target)
        ids_to_delete = [cp.checkpoint_id for cp in checkpoints[target_idx + 1 :]]

        if not ids_to_delete:
            return

        # Delete from SQLite database
        cursor = self._conn.cursor()
        placeholders = ",".join("?" * len(ids_to_delete))

        # Delete from checkpoints table
        cursor.execute(
            f"DELETE FROM checkpoints WHERE thread_id = ? AND checkpoint_id IN ({placeholders})",
            [thread_id] + ids_to_delete,
        )

        # Delete from checkpoint_writes table
        cursor.execute(
            f"DELETE FROM checkpoint_writes WHERE thread_id = ? AND checkpoint_id IN ({placeholders})",
            [thread_id] + ids_to_delete,
        )

        # Delete from checkpoint_blobs table if exists
        try:
            cursor.execute(
                f"DELETE FROM checkpoint_blobs WHERE thread_id = ? AND checkpoint_id IN ({placeholders})",
                [thread_id] + ids_to_delete,
            )
        except Exception:
            pass  # Table might not exist

        self._conn.commit()

    def _revert_operation(self, op: FileOperation) -> None:
        """Revert a single file operation"""
        path = Path(op.file_path)

        if op.operation_type == "write":
            # For write operations, delete the file
            if path.exists():
                path.unlink()
        elif op.operation_type in ("edit", "multi_edit"):
            # For edit operations, restore before_content
            if op.before_content is not None:
                # Ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(op.before_content, encoding="utf-8")
            elif not path.exists():
                # File was created by edit (shouldn't happen normally)
                pass
        else:
            raise ValueError(f"Unknown operation type: {op.operation_type}")

    def get_thread_summary(self, thread_id: str) -> dict:
        """Get summary info for a thread"""
        checkpoints = self.get_checkpoints(thread_id)
        operations = self.recorder.get_operations_for_thread(thread_id)

        # Count unique files modified
        files_modified = set(op.file_path for op in operations)

        return {
            "thread_id": thread_id,
            "checkpoint_count": len(checkpoints),
            "operation_count": len(operations),
            "files_modified": len(files_modified),
            "first_checkpoint": checkpoints[0].timestamp if checkpoints else None,
            "last_checkpoint": checkpoints[-1].timestamp if checkpoints else None,
        }
