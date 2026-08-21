#!/bin/bash
# Quant Dev API Server 啟動腳本
# 用法: ./run.sh [--port PORT] [--host HOST]


# 預設值
PORT=8000
HOST="0.0.0.0"

# 解析 command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        *)
            echo "未知參數: $1"
            echo "用法: ./run.sh [--port PORT] [--host HOST]"
            exit 1
            ;;
    esac
done

# 搵到專案 root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================================
# 🔧 清理舊 process（避免 ngrok port 衝突）
# ============================================================
echo "🧹 清理舊 process..."

# 1. Kill ngrok
if command -v pkill &> /dev/null; then
    pkill -9 ngrok 2>/dev/null
    echo "   ✅ ngrok killed"
else
    killall ngrok 2>/dev/null
    echo "   ✅ ngrok killed (killall)"
fi

# 2. Kill python server
pkill -9 -f "python -m quant_dev" 2>/dev/null
echo "   ✅ quant_dev killed"

# 3. Kill 任何佔用 port 嘅 process
if command -v lsof &> /dev/null; then
    PORT_PID=$(lsof -t -i :$PORT 2>/dev/null)
    if [ -n "$PORT_PID" ]; then
        kill -9 $PORT_PID 2>/dev/null
        echo "   ✅ Port $PORT freed"
    fi
fi

# 4. 刪除舊 PID file
rm -f quant_dev.pid

# 5. 用 pyngrok 嘅 kill（如果有裝）
python -c "from pyngrok import ngrok; ngrok.kill()" 2>/dev/null
echo "   ✅ pyngrok cleaned"

echo ""

# ============================================================
# 🚀 起 server
# ============================================================
echo "🚀 啟動 Quant Dev API Server..."
echo "   Port: $PORT"
echo "   Host: $HOST"
echo "   Log: nohup.out"

nohup /home/ipython168_gmail_com/Projects/quant-dev-git/.venv/bin/python -u -m quant_dev --port "$PORT" --host "$HOST" > nohup.out 2>&1 &

# 記錄 PID
echo $! > quant_dev.pid



# ============================================================
# 🌐 顯示 URL
# ============================================================
echo ""
echo "⏳ 等待 server 啟動..."
sleep 4

# 抽 ngrok URL
NGROK_URL=$(grep -o "https://[a-z0-9-]*\.ngrok-free\.dev" nohup.out | head -1)

if [ -n "$NGROK_URL" ]; then
    echo "============================================================"
    echo "🌐 用手機開呢個 URL:"
    echo "   $NGROK_URL"
    echo "============================================================"
    echo ""
    echo "📡 可用 Endpoints:"
    echo "   GET  $NGROK_URL/"
    echo "   GET  $NGROK_URL/strategies"
    echo "   POST $NGROK_URL/data?ticker=AAPL&days=500"
    echo "   POST $NGROK_URL/backtest"
    echo "   Swagger UI: $NGROK_URL/docs"
    echo ""
else
    echo "⚠️ 未搵到 ngrok URL，請檢查 log:"
    echo "   tail -f nohup.out"
fi

echo "📋 Server PID: $(cat quant_dev.pid)"
echo "📋 睇 log: tail -f nohup.out"
echo "🛑 停止: 請使用 stop.sh"








