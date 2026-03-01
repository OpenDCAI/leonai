"""File operation recorder for time travel functionality"""

from contextvars import ContextVar
from pathlib import Path

from storage.contracts import FileOperationRepo
from storage.models import FileOperationRow
from storage.providers.sqlite.file_operation_repo import SQLiteFileOperationRepo

# Context variable for tracking current thread (TUI only; web uses sandbox.thread_context)
current_thread_id: ContextVar[str] = ContextVar("current_thread_id", default="")


class FileOperationRecorder:
    """Records file operations for time travel rollback"""

    def __init__(self, db_path: Path | str | None = None, repo: FileOperationRepo | None = None):
        # @@@repo-injection - accept pre-built repo (e.g. Supabase) from StorageContainer; fall back to SQLite for TUI.
        if repo is not None:
            self._repo = repo
            self.db_path = None
            return
        if db_path is None:
            db_path = Path.home() / ".leon" / "leon.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._repo = SQLiteFileOperationRepo(self.db_path)

    def record(
        self,
        thread_id: str,
        checkpoint_id: str,
        operation_type: str,
        file_path: str,
        before_content: str | None,
        after_content: str,
        changes: list[dict] | None = None,
    ) -> str:
        return self._repo.record(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            operation_type=operation_type,
            file_path=file_path,
            before_content=before_content,
            after_content=after_content,
            changes=changes,
        )

    def get_operations_for_thread(self, thread_id: str, status: str = "applied") -> list[FileOperationRow]:
        return self._repo.get_operations_for_thread(thread_id, status=status)

    def get_operations_after_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperationRow]:
        return self._repo.get_operations_after_checkpoint(thread_id, checkpoint_id)

    def get_operations_between_checkpoints(
        self, thread_id: str, from_checkpoint_id: str, to_checkpoint_id: str
    ) -> list[FileOperationRow]:
        return self._repo.get_operations_between_checkpoints(thread_id, from_checkpoint_id, to_checkpoint_id)

    def get_operations_for_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperationRow]:
        return self._repo.get_operations_for_checkpoint(thread_id, checkpoint_id)

    def count_operations_for_checkpoint(self, thread_id: str, checkpoint_id: str) -> int:
        return self._repo.count_operations_for_checkpoint(thread_id, checkpoint_id)

    def mark_reverted(self, operation_ids: list[str]) -> None:
        self._repo.mark_reverted(operation_ids)

    def delete_thread_operations(self, thread_id: str) -> int:
        return self._repo.delete_thread_operations(thread_id)


# Global recorder instance (initialized lazily)
_recorder: FileOperationRecorder | None = None


def get_recorder() -> FileOperationRecorder:
    global _recorder
    if _recorder is None:
        _recorder = FileOperationRecorder()
    return _recorder


def set_recorder(recorder: FileOperationRecorder) -> None:
    global _recorder
    _recorder = recorder
