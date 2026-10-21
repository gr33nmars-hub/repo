import os
import sys
import ctypes

if sys.platform == "win32":
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import threading
import time
import json
import random
import uuid
import datetime
import sqlite3
import urllib.request

import fastapi
import fastapi.middleware.cors
import fastapi.staticfiles
import pydantic
import starlette.middleware.cors
import starlette.staticfiles
import uvicorn
import uvicorn.lifespan.off
import uvicorn.lifespan.on
import uvicorn.logging
import uvicorn.loops.auto
import uvicorn.protocols.http.auto
import webview
import webview.platforms.winforms

if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from backend.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="error")

def wait_for_server():
    for _ in range(50):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    wait_for_server()
    
    window = webview.create_window(
        title="NOIR Casino Club",
        url="http://127.0.0.1:8765",
        width=1280,
        height=820,
        min_size=(960, 640),
        background_color="#0d0e12"
    )
    webview.start()
