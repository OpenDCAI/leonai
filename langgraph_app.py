"""
LangGraph Dev 入口文件

用于 langgraph dev 命令的独立入口，不污染 agent.py
"""

from agent import create_leon_agent

# 创建 agent 实例供 langgraph dev 使用
agent = create_leon_agent(profile="profiles/default.yaml").agent
