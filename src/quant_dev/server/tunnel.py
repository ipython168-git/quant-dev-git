# quant_dev/server/tunnel.py

"""
ngrok tunnel 管理
"""
import os
import sys
from pyngrok import ngrok


def get_ngrok_token() -> str:
    """搵 ngrok auth token（多種方法）"""
    token = None

    # 方法 1: .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        token = os.environ.get('NGROK_TOKEN')
        if token:
            print("✅ 從 .env 拎到 token")
            return token
    except:
        pass

    # 方法 2: Colab Secrets
    try:
        from google.colab import userdata
        token = userdata.get('ngrok')
        print("✅ 從 Colab Secrets 拎到 token")
        return token
    except Exception as e:
        print(f"⚠️ Colab Secrets 唔 work: {e}")

    # 方法 3: 環境變數
    token = os.environ.get('NGROK_AUTHTOKEN')
    if token:
        print("✅ 從環境變數拎到 token")
        return token

    # 方法 4: 手動輸入
    print("\n" + "="*60)
    print("⚠️ 請輸入你嘅 ngrok authtoken:")
    print("   (去 https://dashboard.ngrok.com/get-started/your-authtoken 拎)")
    print("="*60)
    token = input("貼你個 token: ").strip()
    return token


def setup_ngrok(port: int = 8000) -> str:
    """設定 ngrok 並開 tunnel，回傳 public URL"""
    token = get_ngrok_token()

    if not token:
        print("❌ 冇 token，請重新執行")
        sys.exit(1)

    ngrok.set_auth_token(token)
    print("✅ ngrok auth 已設定")

    tunnel = ngrok.connect(port)
    return tunnel.public_url


def print_endpoints(url: str):
    """印出可用 endpoints"""
    print("\n" + "="*60)
    print("🌐 用手機開呢個 URL:")
    print(f"   {url}")
    print("="*60)
    print("\n📡 可用 Endpoints:")
    print(f"   GET  {url}/")
    print(f"   GET  {url}/strategies")
    print(f"   POST {url}/data/download?ticker=AAPL&days=500")
    print(f"   POST {url}/backtest")
    print("="*60)












    