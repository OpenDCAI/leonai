"""
Leon 配置管理模块
"""

import os
from pathlib import Path


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
                os.environ[key] = value


def interactive_config():
    """交互式配置"""
    manager = ConfigManager()
    
    print("🔧 Leon 配置向导\n")
    
    api_key = input("请输入 OPENAI_API_KEY: ").strip()
    if api_key:
        manager.set("OPENAI_API_KEY", api_key)
        print("✅ API Key 已保存")
    
    base_url = input("请输入 OPENAI_BASE_URL (可选，直接回车跳过): ").strip()
    if base_url:
        manager.set("OPENAI_BASE_URL", base_url)
        print("✅ Base URL 已保存")
    
    model_name = input("请输入 MODEL_NAME (可选，默认 claude-sonnet-4-5-20250929): ").strip()
    if model_name:
        manager.set("MODEL_NAME", model_name)
        print("✅ Model Name 已保存")
    elif not manager.get("MODEL_NAME"):
        manager.set("MODEL_NAME", "claude-sonnet-4-5-20250929")
        print("✅ 使用默认模型")
    
    print(f"\n✨ 配置已保存到: {manager.config_file}")
    print("\n现在可以直接运行 leonai 命令了！")


def show_config():
    """显示当前配置"""
    manager = ConfigManager()
    config = manager.list_all()
    
    if not config:
        print("❌ 未找到配置，请先运行: leonai config")
        return
    
    print("📋 当前配置:\n")
    for key, value in config.items():
        if "KEY" in key.upper():
            masked_value = value[:8] + "..." if len(value) > 8 else "***"
            print(f"  {key} = {masked_value}")
        else:
            print(f"  {key} = {value}")
    
    print(f"\n配置文件: {manager.config_file}")


def main():
    """配置命令入口"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_config()
    else:
        interactive_config()


if __name__ == "__main__":
    main()
