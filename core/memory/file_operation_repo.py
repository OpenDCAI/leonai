"""Compatibility shim for SQLite file operation repo."""

from core.storage.providers.sqlite.file_operation_repo import FileOperationRow, SQLiteFileOperationRepo

__all__ = ["FileOperationRow", "SQLiteFileOperationRepo"]

