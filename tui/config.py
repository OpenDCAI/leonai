"""
Leon 配置管理模块
"""

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text


console = Console()


class ConfigManager:
    """管理 Leon 的配置"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".leon"
        self.config_file = self.config_dir / "config.env"
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> str | None:
        """获取配置值"""
        if not self.config_file.exists():
            return None
        
        for line in self.config_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip()
        return None
    
    def set(self, key: str, value: str):
        """设置配置值"""
        config = {}
        
        if self.config_file.exists():
            for line in self.config_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
        
        config[key] = value
        
        with self.config_file.open("w") as f:
            for k, v in config.items():
                f.write(f"{k}={v}\n")
    
    def list_all(self) -> dict[str, str]:
        """列出所有配置"""
        config = {}
        if self.config_file.exists():
            for line in self.config_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
        return config
    
    def load_to_env(self):
        """加载配置到环境变量"""
        for key, value in self.list_all().items():
            if key not in os.environ:
                # 规范化 OPENAI_BASE_URL：确保包含 /v1
                if key == "OPENAI_BASE_URL" and value:
                    value = normalize_base_url(value)
                os.environ[key] = value


def normalize_base_url(url: str) -> str:
    """
    规范化 OpenAI 兼容 API 的 base_url

    OpenAI SDK 会在 base_url 后直接拼接 /chat/completions，
    所以 base_url 必须以 /v1 结尾。

    Examples:
        https://api.openai.com -> https://api.openai.com/v1
        https://yunwu.ai -> https://yunwu.ai/v1
        https://yunwu.ai/v1 -> https://yunwu.ai/v1 (不变)
        https://example.com/api/v1 -> https://example.com/api/v1 (不变)
    """
    if not url:
        return url

    url = url.rstrip("/")

    # 如果已经以 /v1 结尾，不处理
    if url.endswith("/v1"):
        return url

    # 如果包含 /v1/ 在中间（如 /v1/engines），不处理
    if "/v1/" in url:
        return url

    # 否则补全 /v1
    return f"{url}/v1"


def interactive_config():
    """交互式配置"""
    manager = ConfigManager()

    # 标题
    title = Text()
    title.append("⚡ ", style="bright_yellow")
    title.append("Leon", style="bold bright_cyan")
    title.append(" 配置向导", style="bold white")

    console.print()
    console.print(Panel(
        "[dim]OpenAI 兼容格式 API · 直接回车使用默认值[/dim]",
        title=title,
        border_style="bright_blue",
        padding=(0, 2),
    ))
    console.print()

    try:
        # 1. API Key（必填）
        current_key = manager.get("OPENAI_API_KEY")
        if current_key:
            masked = current_key[:8] + "..." if len(current_key) > 8 else "***"
            api_key = Prompt.ask(
                f"  [bright_cyan]1.[/] API_KEY",
                default=masked,
                show_default=True,
                console=console,
            )
            if api_key != masked:
                manager.set("OPENAI_API_KEY", api_key)
        else:
            api_key = Prompt.ask(
                "  [bright_cyan]1.[/] API_KEY",
                console=console,
            )
            if api_key:
                manager.set("OPENAI_API_KEY", api_key)
            else:
                console.print("\n  [red]✗[/] API_KEY 是必填项")
                return

        # 2. BASE_URL（可选）
        current_url = manager.get("OPENAI_BASE_URL") or ""
        default_url = current_url or "https://api.openai.com/v1"
        base_url = Prompt.ask(
            "  [bright_cyan]2.[/] BASE_URL [dim](需包含 /v1)[/]",
            default=default_url,
            show_default=True,
            console=console,
        )
        if base_url:
            # 规范化 URL
            normalized = normalize_base_url(base_url)
            if normalized != base_url:
                console.print(f"      [dim]→ 已自动补全为: {normalized}[/]")
            if normalized != current_url:
                manager.set("OPENAI_BASE_URL", normalized)

        # 3. MODEL_NAME（可选）
        current_model = manager.get("MODEL_NAME") or ""
        default_model = current_model or "claude-sonnet-4-5-20250929"
        model_name = Prompt.ask(
            "  [bright_cyan]3.[/] MODEL_NAME",
            default=default_model,
            show_default=True,
            console=console,
        )
        if model_name and model_name != default_model:
            manager.set("MODEL_NAME", model_name)
        elif not current_model:
            manager.set("MODEL_NAME", default_model)

        console.print()
        console.print(f"  [green]✓[/] 已保存到 [dim]{manager.config_file}[/dim]")
        console.print()

    except KeyboardInterrupt:
        console.print("\n\n  [dim]已取消[/dim]\n")
        return


def show_config():
    """显示当前配置"""
    manager = ConfigManager()
    config = manager.list_all()

    if not config:
        console.print("\n  [red]✗[/] 未找到配置，请先运行: [cyan]leonai config[/]\n")
        return

    console.print()
    console.print(Panel(
        "\n".join(
            f"  [bright_cyan]{k}[/] = [dim]{v[:8] + '...' if 'KEY' in k.upper() and len(v) > 8 else v}[/dim]"
            for k, v in config.items()
        ),
        title="[bold]📋 当前配置[/]",
        border_style="bright_blue",
        padding=(0, 2),
    ))
    console.print(f"  [dim]配置文件: {manager.config_file}[/dim]")
    console.print()


def main():
    """配置命令入口"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_config()
    else:
        interactive_config()


if __name__ == "__main__":
    main()
