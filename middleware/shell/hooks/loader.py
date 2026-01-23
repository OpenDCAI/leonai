"""
Bash Hook 加载器

自动发现并加载 bash_hooks 目录下的所有 hook 插件。
"""

import importlib
import inspect
from pathlib import Path

from .base import BashHook


def load_hooks(
    hooks_dir: Path | str | None = None,
    workspace_root: Path | str | None = None,
    **hook_kwargs,
) -> list[BashHook]:
    """
    自动加载所有 bash hook 插件

    Args:
        hooks_dir: hooks 目录路径（默认为当前模块目录）
        workspace_root: 工作目录路径（传递给所有 hooks）
        **hook_kwargs: 传递给 hooks 的额外参数

    Returns:
        按 priority 排序的 hook 实例列表
    """
    if hooks_dir is None:
        hooks_dir = Path(__file__).parent
    else:
        hooks_dir = Path(hooks_dir)

    hooks: list[BashHook] = []

    # 遍历所有 .py 文件
    for py_file in hooks_dir.glob("*.py"):
        # 跳过特殊文件
        if py_file.name.startswith("_") or py_file.name in ["base.py", "loader.py"]:
            continue

        try:
            # 动态导入模块
            module_name = f"middleware.shell.hooks.{py_file.stem}"
            module = importlib.import_module(module_name)

            # 查找所有 BashHook 子类
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 跳过 BashHook 基类本身
                if obj is BashHook:
                    continue

                # 检查是否是 BashHook 的子类
                if issubclass(obj, BashHook) and obj.__module__ == module.__name__:
                    # 实例化 hook
                    hook_instance = obj(workspace_root=workspace_root, **hook_kwargs)

                    # 只添加启用的 hooks
                    if hook_instance.enabled:
                        hooks.append(hook_instance)
                        print(f"[BashHooks] Loaded: {hook_instance.name} (priority={hook_instance.priority})")

        except Exception as e:
            print(f"[BashHooks] Failed to load {py_file.name}: {e}")
            continue

    # 按 priority 排序（数字越小越先执行）
    hooks.sort(key=lambda h: h.priority)

    print(f"[BashHooks] Total {len(hooks)} hooks loaded")
    return hooks


def discover_hooks() -> list[str]:
    """
    发现所有可用的 hook 插件（不加载）

    Returns:
        hook 文件名列表
    """
    hooks_dir = Path(__file__).parent
    hook_files = []

    for py_file in hooks_dir.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name in ["base.py", "loader.py"]:
            continue
        hook_files.append(py_file.stem)

    return hook_files
