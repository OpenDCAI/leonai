#!/bin/bash
# 小猫指物启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🐱 小猫指物 - 启动中..."
echo ""

# Check if Next.js is already running
if lsof -i :3000 > /dev/null 2>&1; then
    echo "✓ Next.js 已在 http://localhost:3000 运行"
else
    echo "启动 Next.js 动画应用..."
    cd "$SCRIPT_DIR/next-app"
    npm run dev &
    NEXT_PID=$!
    echo "✓ Next.js 启动中 (PID: $NEXT_PID)"
    sleep 3
fi

echo ""
echo "启动 Leon Agent..."
cd "$PROJECT_ROOT"
uv run leonai --profile profiles/cat-pointer.yaml

# Cleanup on exit
trap "kill $NEXT_PID 2>/dev/null" EXIT
