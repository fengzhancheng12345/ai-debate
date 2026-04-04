"""启动辩论系统"""
import subprocess
import sys
import os

def check_api_config():
    """检查 API 配置，必须配置了至少一个 API 才能运行"""
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    api_key = ""
    if os.path.exists(config_file):
        import json
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                api_key = cfg.get("api_key", "")
        except Exception:
            pass
    
    if not api_key or api_key == "YOUR_KEY_HERE" or api_key.strip() == "":
        print()
        print("=" * 50)
        print("  [错误] 未检测到有效的 API 配置")
        print("=" * 50)
        print()
        print("请先配置 API Key:")
        print()
        print("  方式一: 编辑 config.json 文件")
        print(f"    路径: {config_file}")
        print('    内容: {"api_key": "你的API密钥", "provider": "minimax"}')
        print()
        print("  方式二: 设置环境变量")
        print("    set MINIMAX_API_KEY=你的密钥")
        print()
        print("支持的 API 提供商: MiniMax, DeepSeek, OpenAI, Claude")
        print()
        return False
    
    return True

def main():
    print("=" * 50)
    print("  AI 辩论系统 v2.0")
    print("=" * 50)
    
    # Check dependencies
    try:
        import fastapi
        import uvicorn
        import requests
        print("[OK] FastAPI, Uvicorn, Requests")
    except ImportError as e:
        print(f"[错误] 缺少依赖: {e}")
        print("安装: pip install fastapi uvicorn requests")
        return
    
    # Check API config
    if not check_api_config():
        return
    
    # Start server
    port = 8098
    print(f"\nAPI 配置检查通过")
    print(f"启动服务: http://0.0.0.0:{port}")
    print(f"访问地址: http://localhost:{port}")
    print()
    
    import server
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
