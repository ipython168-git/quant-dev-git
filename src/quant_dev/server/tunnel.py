# quant_dev/server/tunnel.py

"""
ngrok tunnel management
"""
import os
import sys
from pyngrok import ngrok


def get_ngrok_token() -> str:
    """Retrieve ngrok auth token (multiple methods)."""
    token = None

    # Method 1: .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        token = os.environ.get('NGROK_TOKEN')
        if token:
            print("✅ 從 .env 拎到 token")
            return token
    except:
        pass

    # Method 2: Colab Secrets
    try:
        from google.colab import userdata
        token = userdata.get('ngrok')
        print("✅ 從 Colab Secrets 拎到 token")
        return token
    except Exception as e:
        print(f"⚠️ Colab Secrets 唔 work: {e}")

    # Method 3: Environment variable
    token = os.environ.get('NGROK_AUTHTOKEN')
    if token:
        print("✅ 從環境變數拎到 token")
        return token

    # Method 4: Manual input
    print("\n" + "="*60)
    print("⚠️ Please enter your ngrok authtoken:")
    print("   (Get it from https://dashboard.ngrok.com/get-started/your-authtoken)")
    print("="*60)
    token = input("Paste your token: ").strip()
    return token


def setup_ngrok(port: int = 8000) -> str:
    """Configure ngrok and open tunnel, return public URL"""
    token = get_ngrok_token()

    if not token:
        print("❌ No token found, please try again")
        sys.exit(1)

    ngrok.set_auth_token(token)
    print("✅ ngrok auth configured")

    tunnel = ngrok.connect(port)
    return tunnel.public_url


def print_endpoints(url: str):
    """Print available endpoints"""
    print("\n" + "="*60)
    print("🌐 Open this URL on your phone:")
    print(f"   {url}")
    print("="*60)
    print("\n📡 Available Endpoints:")
    print(f"   GET  {url}/")
    print(f"   GET  {url}/strategies")
    print(f"   POST {url}/data/download?ticker=AAPL&days=500")
    print(f"   POST {url}/backtest")
    print("="*60)












    