"""
辩论系统看门狗 - 自动检测并重启挂掉的服务器
用法: python watchdog.py
"""
import os, sys, socket, subprocess, time, logging

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchdog.log")
CHECK_INTERVAL = 30  # 每30秒检查一次
RESTART_COOLDOWN = 10  # 重启后等待10秒再检查

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("watchdog")

def is_port_open(host="127.0.0.1", port=8098):
    s = socket.socket()
    r = s.connect_ex((host, port))
    s.close()
    return r == 0

def start_server():
    logger.info("🚀 启动辩论服务器...")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchdog_stdout.log"), "w"),
        stderr=open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchdog_stderr.log"), "w"),
    )
    return proc

def main():
    logger.info(f"🦆 看门狗启动！每{CHECK_INTERVAL}秒检查一次端口8098...")
    
    # 启动时确保服务器在运行
    if not is_port_open():
        logger.info("服务器未运行，正在启动...")
        proc = start_server()
        time.sleep(RESTART_COOLDOWN)
        if is_port_open():
            logger.info("✅ 服务器启动成功！")
        else:
            logger.error("❌ 服务器启动失败！")
    else:
        logger.info("✅ 服务器已在运行")

    consecutive_failures = 0

    while True:
        time.sleep(CHECK_INTERVAL)
        if is_port_open():
            consecutive_failures = 0
            # 随机打盹，每10次正常检查才记一次日志（减少噪音）
            if os.environ.get("DEBUG_WATCHDOG"):
                logger.info("✅ 端口正常")
        else:
            consecutive_failures += 1
            logger.warning(f"⚠️ 端口无响应（连续第{consecutive_failures}次）")
            if consecutive_failures >= 2:  # 连续2次（60秒）无响应才重启
                logger.warning("🔄 重启服务器...")
                # 杀掉旧进程
                for line in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.decode().split("\n"):
                    if "python" in line.lower():
                        try:
                            pid = int(line.split()[1])
                            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                        except:
                            pass
                time.sleep(3)
                proc = start_server()
                time.sleep(RESTART_COOLDOWN)
                if is_port_open():
                    consecutive_failures = 0
                    logger.info("✅ 服务器重启成功！")
                else:
                    logger.error("❌ 重启失败，下次循环再试")

if __name__ == "__main__":
    main()
