"""启动辩论系统"""
import subprocess
import sys
import os

def main():
    print("=" * 50)
    print("  AI 辩论系统")
    print("=" * 50)
    print()
    
    # Check dependencies
    try:
        import fastapi
        import uvicorn
        import requests
        print("[OK] FastAPI, Uvicorn, Requests")
    except ImportError as e:
        print(f"[MISSING] {e}")
        print("Install with: pip install fastapi uvicorn requests")
        return
    
    # Start server
    port = 8098
    print(f"\nStarting server on http://0.0.0.0:{port}")
    print(f"Open: http://localhost:{port}\n")
    
    import server
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()