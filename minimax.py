"""MiniMax Anthropic-compatible API client"""
import requests
from typing import Optional, List, Dict, Any

class MiniMaxClient:
    def __init__(self, api_key: str, base_url: str, model: str, max_tokens: int, timeout: int):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.url = f"{base_url}/v1/messages"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-path-access": "true",
        }

    def chat(self, messages: List[Dict[str, str]], system: str = "", max_tokens: int = None) -> str:
        """Send a chat request, return the text content"""
        body = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": []
        }
        if system:
            body["messages"].append({"role": "system", "content": system})
        body["messages"].extend(messages)
        
        try:
            r = requests.post(self.url, json=body, headers=self.headers, timeout=self.timeout)
            if r.status_code == 200:
                resp = r.json()
                for block in resp.get("content", []):
                    if block.get("type") == "text":
                        return block.get("text", "")
                return ""
            elif r.status_code == 429:
                return f"[Error: Rate limited, please wait]"
            else:
                return f"[Error: {r.status_code}] {r.text[:200]}"
        except requests.exceptions.Timeout:
            return "[Error: Request timeout]"
        except Exception as e:
            return f"[Error: {e}]"

    def stream_chat(self, messages: List[Dict[str, str]], system: str = ""):
        """Streaming chat - yields text chunks as they come"""
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": []
        }
        if system:
            body["messages"].append({"role": "system", "content": system})
        body["messages"].extend(messages)
        
        try:
            import requests
            r = requests.post(self.url, json=body, headers=self.headers, stream=True, timeout=self.timeout)
            if r.status_code != 200:
                yield f"[Error: {r.status_code}]"
                return
            
            # SSE streaming response
            buffer = b""
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    buffer += chunk
                    # Process complete lines
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line = line.strip()
                        if line.startswith(b"data:"):
                            import json
                            data_str = line[5:].strip()
                            try:
                                data = json.loads(data_str)
                                # Handle SSE event format from MiniMax
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield delta.get("text", "")
                            except:
                                pass
        except Exception as e:
            yield f"[Error: {e}]"