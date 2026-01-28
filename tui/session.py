"""Session management for TUI resume"""
import json
from pathlib import Path
from typing import Optional


class SessionManager:
    """管理 TUI session 状态"""

    def __init__(self, session_dir: Path | None = None):
        if session_dir is None:
            session_dir = Path.home() / ".config" / "leon"
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / "session.json"

    def save_session(self, thread_id: str, workspace: str | None = None) -> None:
        """保存 session 状态"""
        data = self._load_data()
        data["last_thread_id"] = thread_id

        # 更新 thread 列表（最多保留 20 个）
        threads = data.get("threads", [])
        if thread_id not in threads:
            threads.insert(0, thread_id)
            threads = threads[:20]
            data["threads"] = threads

        if workspace:
            data["last_workspace"] = workspace

        self.session_file.write_text(json.dumps(data, indent=2))

    def get_last_thread_id(self) -> Optional[str]:
        """获取最后使用的 thread_id"""
        data = self._load_data()
        return data.get("last_thread_id")

    def get_threads(self) -> list[str]:
        """获取所有 thread_id 列表"""
        data = self._load_data()
        return data.get("threads", [])

    def _load_data(self) -> dict:
        """加载 session 数据"""
        if not self.session_file.exists():
            return {}
        try:
            return json.loads(self.session_file.read_text())
        except Exception:
            return {}
