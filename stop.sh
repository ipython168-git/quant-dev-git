#!/bin/bash
# 停止 Quant Dev API Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "quant_dev.pid" ]; then
    PID=$(cat quant_dev.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "🛑 停止 Server (PID: $PID)..."
        kill "$PID"
        rm -f quant_dev.pid
        echo "✅ Server 已停止"
    else
        echo "⚠️ Process $PID 不存在，刪除 PID file"
        rm -f quant_dev.pid
    fi
else
    echo "⚠️ 未找到 quant_dev.pid"
fi

# 額外清理：kill 任何殘留 ngrok / uvicorn
echo "🧹 額外清理..."
pkill -9 ngrok 2>/dev/null
pkill -9 -f "python -m quant_dev" 2>/dev/null
if command -v lsof &> /dev/null; then
    PORT_PID=$(lsof -t -i :8000 2>/dev/null)
    [ -n "$PORT_PID" ] && kill -9 $PORT_PID 2>/dev/null
fi
echo "✅ 清理完成"