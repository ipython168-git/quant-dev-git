# quant_dev/server/runner.py
"""
Server runner
"""
import time
import threading
import uvicorn


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "info",
    reload: bool = False,
):
    """喺 background thread 起 server"""
    from quant_dev.api.app import app

    def _run():
        uvicorn.run(
            app, 
            host=host, 
            port=port, 
            log_level=log_level,
            reload=reload,
        )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    time.sleep(2)
    print(f"\n✅ Server 已起好 (http://{host}:{port})")
    return thread

 











    