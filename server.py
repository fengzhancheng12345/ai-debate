"""辩论系统 - FastAPI 服务器"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio

from config import HOST, PORT, MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, MINIMAX_MAX_TOKENS, MINIMAX_TIMEOUT
from minimax import MiniMaxClient
from store import store
from agents import run_debate_stream

# Create FastAPI app
app = FastAPI(title="AI辩论系统", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MiniMax client
client = MiniMaxClient(
    api_key=MINIMAX_API_KEY,
    base_url=MINIMAX_BASE_URL,
    model=MINIMAX_MODEL,
    max_tokens=MINIMAX_MAX_TOKENS,
    timeout=MINIMAX_TIMEOUT
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

@app.post("/api/debate/analyze")
async def analyze_topic(data: dict):
    """Use AI to analyze topic and dynamically generate form fields"""
    topic = data.get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    
    prompt = f"""用户要辩论的话题：{topic}

请分析这个话题，判断辩论需要了解用户的哪些背景信息。

要求：
- 只输出JSON，不要任何其他内容
- 根据话题特点，动态决定需要哪些字段
- 字段数量：3-6个为宜（太少信息不够，太多太复杂）
- 字段类型：
  * text: 用户需要输入文字（适合无固定选项的内容）
  * select: 用户从选项中选择（适合有标准选项的内容）
  * textarea: 需要较长文字说明的内容
- 每个select字段需要提供options数组（3-6个选项）
- placeholders要具体、有针对性，不要泛泛的"请输入"
- 总共不超过10个字段

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
        
        import re, json as json_module
        try:
            m = re.search(r'\{.*\}', result, re.DOTALL)
            if m:
                analysis = json_module.loads(m.group())
            else:
                analysis = None
        except:
            analysis = None
        
        if not analysis or "fields" not in analysis:
            # Fallback: basic 3-field structure
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
    """Start a new debate session"""
    topic = data.get("topic", "").strip()
    user_input = data.get("user_input", "").strip()
    
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    
    session_id = store.create_session(topic, user_input)
    return {"success": True, "session_id": session_id, "topic": topic}

@app.get("/api/debate/{session_id}/stream")
def stream_debate(session_id: str):
    """SSE stream - uses a queue to bridge sync generator with async response"""
    import queue
    import threading
    import json as _json

    q = queue.Queue()
    error = [None]

    def run_in_thread():
        """Run the sync generator in a background thread"""
        try:
            for event in run_debate_stream(session_id, client):
                q.put(event)
            q.put(None)  # sentinel: end of stream
        except Exception as e:
            error[0] = e
            q.put(None)

    t = threading.Thread(target=run_in_thread, daemon=True)
    t.start()

    def generate():
        """Yield SSE-formatted events from the queue"""
        try:
            while True:
                try:
                    event = q.get(timeout=0.5)
                except queue.Empty:
                    if error[0]:
                        err = _json.dumps({"type": "error", "data": {"message": str(error[0])}}, ensure_ascii=False)
                        yield f"data: {err}\n\n".encode()
                        break
                    # No ping - keep waiting; EventSource handles keepalive
                    continue

                if event is None:
                    end = _json.dumps({"type": "stream_end"}, ensure_ascii=False)
                    yield f"data: {end}\n\n".encode()
                    break

                data = _json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n".encode()
        except Exception as e:
            err = _json.dumps({"type": "error", "data": {"message": str(e)}}, ensure_ascii=False)
            yield f"data: {err}\n\n".encode()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.get("/api/debate/{session_id}/status")
async def get_status(session_id: str):
    """Get debate session status"""
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
    """Delete/Cleanup a debate session"""
    store.delete_session(session_id)
    return {"success": True}

# ============== Health ==============

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-debate", "version": "1.0"}

# ============== Startup ==============

def main():
    print(f"Starting AI辩论系统 on {HOST}:{PORT}")
    print(f"Access at: http://localhost:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")

if __name__ == "__main__":
    main()
