"""辩论系统 - FastAPI 服务器"""
import os, sys, json, threading, queue
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, requests

from store import store
from agents import run_debate_stream

# ============== API Provider Config ==============

PROVIDERS = {
    "minimax": {
        "name": "MiniMax",
        "url_label": "API 地址",
        "url_placeholder": "https://api.minimax.io/anthropic",
        "url_default": "https://api.minimax.io/anthropic",
        "models": [
            {"id": "MiniMax-M2.7", "name": "MiniMax M2.7 (推荐)"},
            {"id": "MiniMax-M2.5", "name": "MiniMax M2.5"},
        ],
        "api_format": "anthropic",
        "timeout": 60,
    },
    "deepseek": {
        "name": "DeepSeek",
        "url_label": "API 地址",
        "url_placeholder": "https://api.deepseek.com",
        "url_default": "https://api.deepseek.com",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V3 (推荐)"},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1 (推理)"},
        ],
        "api_format": "openai",
        "timeout": 60,
    },
    "openai": {
        "name": "OpenAI",
        "url_label": "API 地址",
        "url_placeholder": "https://api.openai.com/v1",
        "url_default": "https://api.openai.com/v1",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o (推荐)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (便宜)"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo (便宜)"},
        ],
        "api_format": "openai",
        "timeout": 90,
    },
    "groq": {
        "name": "Groq",
        "url_label": "API 地址",
        "url_placeholder": "https://api.groq.com/openai/v1",
        "url_default": "https://api.groq.com/openai/v1",
        "models": [
            {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B (推荐)"},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B (极速)"},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
        ],
        "api_format": "openai",
        "timeout": 30,
    },
    "openrouter": {
        "name": "OpenRouter",
        "url_label": "API 地址",
        "url_placeholder": "https://openrouter.ai/api/v1",
        "url_default": "https://openrouter.ai/api/v1",
        "models": [
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet (推荐)"},
            {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus"},
            {"id": "google/gemini-pro-1.5", "name": "Gemini Pro 1.5"},
            {"id": "meta-llama/llama-3-70b-instruct", "name": "Llama 3 70B"},
            {"id": "mistralai/mixtral-8x7b-instruct", "name": "Mixtral 8x7B"},
        ],
        "api_format": "openai",
        "timeout": 90,
    },
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ============== Unified API Client ==============

class UnifiedAPIClient:
    """Single client that routes to MiniMax, DeepSeek, OpenAI, Groq, or OpenRouter"""

    def __init__(self, config: dict):
        self.cfg = config or {}
        self._apply_config()

    def _apply_config(self):
        p = self.cfg.get("provider", "minimax")
        meta = PROVIDERS.get(p, PROVIDERS["minimax"])

        self.api_key = self.cfg.get("api_key", "")
        self.base_url = self.cfg.get("base_url", meta["url_default"]).rstrip("/")
        self.model = self.cfg.get("model", meta["models"][0]["id"])
        self.timeout = meta.get("timeout", 60)
        self.api_format = meta.get("api_format", "openai")
        self.provider = p

    def chat(self, messages, system="", max_tokens=None) -> str:
        if not self.api_key or self.api_key == "YOUR_KEY_HERE":
            return "[Error: 未配置 API Key，请点击右上角 ⚙️ 设置]"

        mt = max_tokens or 8000

        if self.api_format == "anthropic":
            return self._chat_anthropic(messages, system, mt)
        else:
            return self._chat_openai(messages, system, mt)

    def _chat_anthropic(self, messages, system, max_tokens):
        """Anthropic messages API (MiniMax)"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-path-access": "true",
        }
        body = {"model": self.model, "max_tokens": max_tokens, "messages": []}
        if system:
            body["messages"].append({"role": "system", "content": system})
        body["messages"].extend(messages)
        try:
            r = requests.post(
                f"{self.base_url}/v1/messages",
                json=body, headers=headers, timeout=self.timeout
            )
            if r.status_code == 200:
                for block in r.json().get("content", []):
                    if block.get("type") == "text":
                        return block.get("text", "")
                return ""
            elif r.status_code == 429:
                return "[Error: Rate limited]"
            else:
                return f"[Error: {r.status_code}] {r.text[:200]}"
        except requests.exceptions.Timeout:
            return "[Error: 请求超时]"
        except Exception as e:
            return f"[Error: {e}]"

    def _chat_openai(self, messages, system, max_tokens):
        """OpenAI chat completions API (DeepSeek, OpenAI, Groq, OpenRouter)"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {"model": self.model, "max_tokens": max_tokens, "messages": []}
        if system:
            body["messages"].insert(0, {"role": "system", "content": system})
        body["messages"].extend(messages)
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                json=body, headers=headers, timeout=self.timeout
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            elif r.status_code == 429:
                return "[Error: Rate limited]"
            else:
                return f"[Error: {r.status_code}] {r.text[:200]}"
        except requests.exceptions.Timeout:
            return "[Error: 请求超时]"
        except Exception as e:
            return f"[Error: {e}]"

    def is_configured(self) -> bool:
        key = self.cfg.get("api_key", "")
        return bool(key and key != "YOUR_KEY_HERE")


# ============== Config Management ==============

_default_config = {
    "provider": "minimax",
    "api_key": "",
    "base_url": "https://api.minimax.io/anthropic",
    "model": "MiniMax-M2.7",
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Merge with defaults
                cfg = dict(_default_config)
                cfg.update(loaded)
                return cfg
        except Exception:
            pass
    return dict(_default_config)

def save_config(cfg: dict) -> dict:
    # Only save non-sensitive fields (api_key is stored but user decides)
    safe = {k: v for k, v in cfg.items() if k in ("provider", "api_key", "base_url", "model")}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2, ensure_ascii=False)
    return safe

# Load config and create global client
_config = load_config()
client = UnifiedAPIClient(_config)


# ============== FastAPI App ==============

app = FastAPI(title="AI 辩论系统", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pages ==============

@app.get("/", response_class=HTMLResponse)
async def home():
    with open(os.path.join(os.path.dirname(__file__), "templates", "debate.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/debate", response_class=HTMLResponse)
async def debate_page():
    with open(os.path.join(os.path.dirname(__file__), "templates", "debate.html"), "r", encoding="utf-8") as f:
        return f.read()


# ============== API ==============

@app.get("/api/config")
async def get_config():
    """Return current config (without exposing full API key)"""
    return {
        "configured": client.is_configured(),
        "provider": client.provider,
        "model": client.model,
        "base_url": client.base_url,
        "key_set": bool(client.api_key and client.api_key != "YOUR_KEY_HERE"),
        "providers": {k: {"name": v["name"], "models": v["models"]} for k, v in PROVIDERS.items()},
    }

@app.post("/api/config")
async def post_config(data: dict):
    """Save new API config"""
    global client, _config

    provider = data.get("provider", "minimax")
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown provider")

    meta = PROVIDERS[provider]
    api_key = data.get("api_key", "").strip()
    base_url = data.get("base_url", meta["url_default"]).strip().rstrip("/")
    model = data.get("model", meta["models"][0]["id"])

    # Validate model
    valid_models = [m["id"] for m in meta["models"]]
    if model not in valid_models:
        model = meta["models"][0]["id"]

    _config = {"provider": provider, "api_key": api_key, "base_url": base_url, "model": model}
    save_config(_config)
    client = UnifiedAPIClient(_config)

    return {"success": True, "provider": provider, "model": model}

@app.post("/api/config/test")
async def test_config(data: dict):
    """Test an API config without saving"""
    provider = data.get("provider", "minimax")
    meta = PROVIDERS.get(provider, PROVIDERS["minimax"])
    api_key = data.get("api_key", "").strip()
    base_url = data.get("base_url", meta["url_default"]).strip().rstrip("/")
    model = data.get("model", meta["models"][0]["id"])

    test_client = UnifiedAPIClient({
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    })

    result = test_client.chat(
        [{"role": "user", "content": "Hello, reply with exactly one word: OK"}],
        system="Reply with exactly one word: OK",
        max_tokens=10,
    )

    ok = not result.startswith("[Error:")
    return {"success": ok, "message": result}


@app.post("/api/debate/analyze")
async def analyze_topic(data: dict):
    topic = data.get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    prompt = f"""用户要辩论的话题：{topic}

请分析这个话题，判断辩论需要了解用户的哪些背景信息。

要求：
- 只输出JSON，不要任何其他内容
- 字段数量：3-6个为宜
- 字段类型：text / select / textarea
- 每个select字段需要提供options数组（3-6个选项）
- placeholders要具体，不要泛泛的"请输入"

请按以下JSON格式回答：
{{
  "fields": [
    {{
      "key": "field_key",
      "label": "字段中文名",
      "type": "text" | "select" | "textarea",
      "description": "给用户的简短说明（5-15字）",
      "placeholder": "输入提示（10-30字，要具体）",
      "options": ["选项1", "选项2", "选项3"]
    }}
  ]
}}"""

    try:
        result = client.chat(
            [{"role": "user", "content": prompt}],
            system="你是一个辩论策划专家，输出纯JSON。"
        )

        import re
        try:
            m = re.search(r'\{.*\}', result, re.DOTALL)
            if m:
                analysis = json.loads(m.group()) if hasattr(json, 'loads') else __import__('json').loads(m.group())
            else:
                analysis = None
        except Exception:
            analysis = None

        if not analysis or "fields" not in analysis:
            analysis = {
                "fields": [
                    {"key": "situation", "label": "个人情况", "type": "textarea",
                     "description": "你的具体情况", "placeholder": "描述你的背景、预算、条件等"},
                    {"key": "angles", "label": "关心的问题", "type": "textarea",
                     "description": "辩论重点", "placeholder": "你希望重点讨论哪些方面"},
                    {"key": "timeframe", "label": "时间范围", "type": "select",
                     "description": "决策时间", "options": ["近期", "半年内", "一年内", "了解中"]}
                ]
            }

        return {"success": True, "topic": topic, "fields": analysis["fields"]}

    except Exception as e:
        return {"error": str(e)}


@app.post("/api/debate/start")
async def start_debate(data: dict):
    topic = data.get("topic", "").strip()
    user_input = data.get("user_input", "").strip()

    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    session_id = store.create_session(topic, user_input)
    return {"success": True, "session_id": session_id, "topic": topic}


@app.get("/api/debate/{session_id}/stream")
def stream_debate(session_id: str):
    q = queue.Queue()
    error = [None]

    def run_in_thread():
        try:
            for event in run_debate_stream(session_id, client):
                q.put(event)
            q.put(None)
        except Exception as e:
            error[0] = e
            q.put(None)

    t = threading.Thread(target=run_in_thread, daemon=True)
    t.start()

    def generate():
        try:
            while True:
                try:
                    event = q.get(timeout=0.5)
                except queue.Empty:
                    if error[0]:
                        err = json.dumps({"type": "error", "data": {"message": str(error[0])}}, ensure_ascii=False)
                        yield f"data: {err}\n\n".encode()
                        break
                    continue

                if event is None:
                    end = json.dumps({"type": "stream_end"}, ensure_ascii=False)
                    yield f"data: {end}\n\n".encode()
                    break

                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n".encode()
        except Exception as e:
            err = json.dumps({"type": "error", "data": {"message": str(e)}}, ensure_ascii=False)
            yield f"data: {err}\n\n".encode()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/api/debate/{session_id}/status")
async def get_status(session_id: str):
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "topic": session.topic,
        "status": session.status,
        "phase": session.current_phase,
        "groups_count": len(session.groups),
    }


@app.delete("/api/debate/{session_id}")
async def delete_session(session_id: str):
    store.delete_session(session_id)
    return {"success": True}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-debate",
        "version": "2.0",
        "provider": client.provider,
        "model": client.model,
        "configured": client.is_configured(),
    }


def main():
    cfg_desc = f"{client.provider}/{client.model}" if client.is_configured() else "NOT CONFIGURED"
    print(f"Starting AI debate system v2.0 on 0.0.0.0:8098")
    print(f"API: {cfg_desc}")
    print(f"Access: http://localhost:8098/debate")
    uvicorn.run(app, host="0.0.0.0", port=8098, log_level="info")

if __name__ == "__main__":
    main()
