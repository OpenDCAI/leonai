"""Backward compatibility — re-exports from split service modules."""

from backend.web.services.member_service import *  # noqa: F401,F403
from backend.web.services.task_service import *  # noqa: F401,F403
from backend.web.services.library_service import *  # noqa: F401,F403
from backend.web.services.profile_service import *  # noqa: F401,F403
from backend.web.services.member_service import ensure_members_dir
from backend.web.services.library_service import ensure_library_dir


def ensure_directories() -> None:
    ensure_members_dir()
    ensure_library_dir()


init_panel_tables = ensure_directories
