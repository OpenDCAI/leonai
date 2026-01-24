#!/bin/bash
# Leon CLI 启动脚本
cd "$(dirname "$0")"
uv run leon "$@"
