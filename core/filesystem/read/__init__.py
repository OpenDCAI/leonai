"""Read subpackage - handles file reading with type-specific strategies."""

from middleware.filesystem.read.dispatcher import read_file
from middleware.filesystem.read.types import FileType, ReadLimits, ReadResult

__all__ = ["FileType", "ReadLimits", "ReadResult", "read_file"]
