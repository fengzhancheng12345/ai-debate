"""配置模板 - 复制为 config.py 后填入真实密钥"""
import os

MINIMAX_API_KEY = "YOUR_MINIMAX_API_KEY_HERE"
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
MINIMAX_MODEL = "MiniMax-M2.7"
MINIMAX_MAX_TOKENS = 8000
MINIMAX_TIMEOUT = 60

HOST = "0.0.0.0"
PORT = 8098
DEBUG = False

PROXY = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or None
