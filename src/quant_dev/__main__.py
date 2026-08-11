# quant_dev/__main__.py
"""
quant_dev 主入口點
用法:
    python -m quant_dev              
    python -m quant_dev --port 8001  # 指定 port
"""
import argparse
import time

from quant_dev.server import (
    setup_ngrok,
    print_endpoints,
    run_server,
)


def main():
    parser = argparse.ArgumentParser(description="Quant Dev API Server")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--reload", action="store_true", help="開發模式，自動 reload")
    args = parser.parse_args()
 
    import nest_asyncio
    nest_asyncio.apply()

    public_url = setup_ngrok(args.port)
    print_endpoints(public_url)

    run_server(args.host, args.port, reload=args.reload) 

    print(f"📱 用手機開: {public_url}")
    print("按 Ctrl+C 停止\n")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Server 已停止")


if __name__ == "__main__":
    main()



