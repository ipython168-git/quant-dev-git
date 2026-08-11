#!/bin/bash
# 檢查 Quant Dev API Server 狀態

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "quant_dev.pid" ]; then
    PID=$(cat quant_dev.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "✅ Server 運行中 (PID: $PID)"
        echo "📋 最近 log:"
        tail -5 nohup.out
    else
        echo "❌ Server 已停止 (PID file 存在但 process 唔存在)"
    fi
else
    echo "❌ Server 未啟動"
fi