# This Python file uses the following encoding: utf-8
# Copy from https://github.com/LmeSzinc/AzurLaneAutoScript/gui.py


"""
在任何平台把当前 Python 进程（含子线程、子进程）切到北京时间。
• Linux/macOS/WSL 及 Win-Py 3.11+ → TZ='Asia/Shanghai' + time.tzset()
• Win-Py ≤ 3.10            → TZ='CST-8'       + _tzset()（POSIX 语法）
"""
import os, sys, time

if hasattr(time, "tzset"):
    # Unix 全系  /  Windows 3.11+ 走这条
    os.environ["TZ"] = "Asia/Shanghai"     # IANA 名称，glibc/Apple libc 都认识
    time.tzset()
else:
    # 只有旧 Windows 才会落到这里
    import ctypes
    os.environ["TZ"] = "CST-8"             # POSIX 字符串：UTC+8 且无 DST
    for dll in ("ucrtbase", "msvcrt"):     # 新旧 CRT 都试一遍
        try:
            ctypes.CDLL(dll)._tzset()
            break
        except (OSError, AttributeError):
            continue
        
import threading

# Keep this ahead of third-party imports: a previous pip failure can otherwise
# prevent the Web update service from ever reaching its recovery code.
if __name__ == '__main__':
    from deploy.first_run import recover_before_imports
    if recover_before_imports():
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__), *sys.argv[1:]])

from module.logger import logger
from module.image.rpc import ensure_image_server_ready, shutdown_image_server
from module.server.setting import State
from module.ocr.rpc import ensure_ocr_server_ready, shutdown_ocr_server


def fun(ev: threading.Event):
    import argparse
    import asyncio
    import sys

    import uvicorn

    # 不知道干啥的照着抄就行了
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    State.restart_event = ev

    parser = argparse.ArgumentParser(description="Alas web service")
    parser.add_argument(
        "--host",
        type=str,
        help="Host to listen. Default to WebuiHost in deploy setting",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port to listen. Default to WebuiPort in deploy setting",
    )
    parser.add_argument(
        "-k", "--key", type=str, help="Password of alas. No password by default"
    )
    parser.add_argument(
        "--cdn",
        action="store_true",
        help="Use jsdelivr cdn for pywebio static files (css, js). Self host cdn by default.",
    )
    parser.add_argument(
        "--run",
        nargs="+",
        type=str,
        help="Run alas by config names on startup",
    )
    args, _ = parser.parse_known_args()

    host = args.host or State.deploy_config.WebuiHost or "0.0.0.0"
    port = args.port or int(State.deploy_config.WebuiPort) or 22270

    logger.hr("Launcher config")
    logger.attr("Host", host)
    logger.attr("Port", port)
    logger.attr("Reload", ev is not None)

    try:
        ensure_image_server_ready()
        try:
            ensure_ocr_server_ready()
        except Exception:
            # The control panel must remain reachable when OCR dependencies or
            # models are missing. OCR requests still report their own failure.
            logger.exception(
                "OCR initialization failed; the web service will remain available. "
                "Install the OCR dependencies/models before running game tasks."
            )
        logger.info('正在加载 Web API；图像和 OCR 就绪后仍需完成后端启动检查')
        if ev is None:
            uvicorn.run("module.server.app:fastapi_app", host=host, port=port,
                        factory=True, log_config=None)
        else:
            web = uvicorn.Server(uvicorn.Config("module.server.app:fastapi_app",
                                 host=host, port=port, factory=True, log_config=None))
            watcher_stop = threading.Event()

            def watch_restart():
                while not watcher_stop.is_set():
                    if ev.wait(0.5):
                        web.should_exit = True
                        return

            watcher = threading.Thread(target=watch_restart, daemon=True)
            watcher.start()
            try:
                web.run()
            finally:
                watcher_stop.set()
                watcher.join(2)
    finally:
        shutdown_image_server()
        shutdown_ocr_server()


if __name__ == "__main__":
    restart = threading.Event()
    fun(restart)
    if restart.is_set():
        # Replace this interpreter after orderly HTTP/task/OCR/image shutdown.
        import json
        if State.update_resume_instances is not None:
            os.environ['OAS_UPDATE_RESUME'] = json.dumps(State.update_resume_instances)
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__), *sys.argv[1:]])
