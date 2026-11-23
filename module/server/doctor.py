# This Python file uses the following encoding: utf-8
"""主动体检: 只读检查运行环境, 不启动服务、不修改配置。

参考上游 pinkpig-Peppa 的 /tool/doctor, 适配本地目录、依赖与多实例配置。
"""
from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_RESOLUTIONS = ((1280, 720), (720, 1280))
GAME_PACKAGE_KEYWORDS = ("onmyoji", "yys")
REQUIRED_MODULES = (
    "fastapi",
    "zerorpc",
    "cv2",
    "numpy",
    "psutil",
    "onepush",
    "adbutils",
    "ppocronnx",
)


def _find_adb() -> str | None:
    for candidate in (shutil.which("adb"), shutil.which("adb.exe")):
        if candidate:
            return candidate
    for relative in (
        "bin/platform-tools/adb.exe",
        "bin/adb.exe",
        "platform-tools/adb.exe",
        "toolkit/adb.exe",
    ):
        path = PROJECT_ROOT / relative
        if path.exists():
            return str(path)
    try:
        from adbutils import adb_path

        path = adb_path()
        if path and Path(path).exists():
            return str(path)
    except Exception:
        pass
    return None


def _run(adb: str, args: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    creationflags = 0x08000000 if os.name == "nt" else 0
    return subprocess.run(
        [adb, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=creationflags,
    )


def _check(name: str, func: Callable[[], tuple[str, str]]) -> dict:
    start = time.perf_counter()
    try:
        status, detail = func()
    except Exception as e:
        status, detail = "fail", f"{type(e).__name__}: {e}"
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
    }


def parse_adb_devices(output: str) -> list[str]:
    serials: list[str] = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def parse_wm_size(output: str) -> list[tuple[int, int]]:
    return [(int(width), int(height)) for width, height in re.findall(r"(\d+)x(\d+)", output)]


def parse_packages(output: str) -> list[str]:
    return [line.split("package:", 1)[1].strip() for line in output.splitlines() if line.startswith("package:")]


def _check_config(config_name: str | None) -> tuple[str, str]:
    config_dir = PROJECT_ROOT / "config"
    files = sorted(config_dir.glob("*.json"))
    if not files:
        return "fail", f"{config_dir} 下没有实例配置"
    if config_name:
        target = config_dir / f"{config_name}.json"
        if not target.exists():
            return "fail", f"实例配置不存在: {target}"
        with target.open("r", encoding="utf-8") as f:
            json.load(f)
        return "pass", f"实例配置可读取: {target.name}"
    return "pass", f"{len(files)} 个实例配置"


def _check_dependencies() -> tuple[str, str]:
    failed = []
    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
        except Exception as e:
            failed.append(f"{name}({type(e).__name__})")
    if failed:
        return "fail", "导入失败: " + ", ".join(failed)
    return "pass", f"{len(REQUIRED_MODULES)} 个依赖可用"


def _check_adb(adb: str | None) -> tuple[str, str]:
    if not adb:
        return "fail", "未找到 adb, 请安装 platform-tools 或配置 PATH"
    result = _run(adb, ["version"], timeout=10)
    if result.returncode != 0:
        return "fail", (result.stderr or result.stdout).strip()[:300]
    first_line = (result.stdout or "").strip().splitlines()[0] if result.stdout.strip() else "adb"
    return "pass", f"{adb} | {first_line}"


def _check_adb_server(adb: str | None) -> tuple[str, str]:
    if not adb:
        return "skip", "adb 不可用"
    result = _run(adb, ["devices"], timeout=15)
    if result.returncode != 0:
        return "fail", (result.stderr or result.stdout).strip()[:300]
    return "pass", "adb server 可响应"


def _check_devices(adb: str | None) -> tuple[str, str]:
    if not adb:
        return "skip", "adb 不可用"
    result = _run(adb, ["devices"], timeout=15)
    if result.returncode != 0:
        return "fail", (result.stderr or result.stdout).strip()[:300]
    serials = parse_adb_devices(result.stdout)
    if not serials:
        return "warn", "adb 可用但没有在线设备"
    return "pass", f"{len(serials)} 台在线: {', '.join(serials)}"


def _check_resolution(adb: str | None) -> tuple[str, str]:
    if not adb:
        return "skip", "adb 不可用"
    result = _run(adb, ["devices"], timeout=15)
    serials = parse_adb_devices(result.stdout) if result.returncode == 0 else []
    if not serials:
        return "skip", "没有在线设备"
    mismatched = []
    for serial in serials:
        size_result = _run(adb, ["-s", serial, "shell", "wm", "size"], timeout=10)
        sizes = parse_wm_size(size_result.stdout)
        if not sizes:
            mismatched.append(f"{serial}: 无法读取")
            continue
        width, height = sizes[-1]
        if (width, height) not in SUPPORTED_RESOLUTIONS:
            mismatched.append(f"{serial}: {width}x{height}")
    if mismatched:
        return "warn", f"目标 1280x720 (或 720x1280), 实际: " + ", ".join(mismatched)
    return "pass", "全部为 1280x720 / 720x1280"


def _check_game(adb: str | None) -> tuple[str, str]:
    if not adb:
        return "skip", "adb 不可用"
    result = _run(adb, ["devices"], timeout=15)
    serials = parse_adb_devices(result.stdout) if result.returncode == 0 else []
    if not serials:
        return "skip", "没有在线设备"
    found: list[str] = []
    for serial in serials:
        package_result = _run(adb, ["-s", serial, "shell", "pm", "list", "packages"], timeout=20)
        if package_result.returncode != 0:
            continue
        for package in parse_packages(package_result.stdout):
            lowered = package.lower()
            if any(keyword in lowered for keyword in GAME_PACKAGE_KEYWORDS):
                found.append(f"{serial}:{package}")
    if not found:
        return "warn", "未检测到阴阳师相关包名"
    return "pass", ", ".join(found[:5])


def _check_image_service() -> tuple[str, str]:
    try:
        from module.image.rpc import get_image_client

        client = get_image_client(refresh=True)
        client.ping()
        return "pass", "图像服务可响应"
    except Exception as e:
        return "warn", f"图像服务未就绪: {type(e).__name__}: {e}"


def _check_ocr_service() -> tuple[str, str]:
    try:
        from module.ocr.rpc import get_ocr_client

        client = get_ocr_client(refresh=True)
        client.ping()
        return "pass", "OCR 服务可响应"
    except Exception as e:
        return "warn", f"OCR 服务未就绪: {type(e).__name__}: {e}"


def _check_disk() -> tuple[str, str]:
    usage = shutil.disk_usage(PROJECT_ROOT)
    free_gb = usage.free / (1024 ** 3)
    if free_gb < 1:
        return "fail", f"剩余空间仅 {free_gb:.1f} GB"
    return "pass", f"剩余 {free_gb:.1f} GB"


def _check_log_dir() -> tuple[str, str]:
    log_dir = PROJECT_ROOT / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    probe = log_dir / ".doctor_probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    return "pass", str(log_dir)


def run_doctor(config_name: str | None = None) -> dict:
    adb = _find_adb()
    checks = [
        _check("config", lambda: _check_config(config_name)),
        _check("dependencies", _check_dependencies),
        _check("adb", lambda: _check_adb(adb)),
        _check("adb_server", lambda: _check_adb_server(adb)),
        _check("devices", lambda: _check_devices(adb)),
        _check("resolution", lambda: _check_resolution(adb)),
        _check("game", lambda: _check_game(adb)),
        _check("image_service", _check_image_service),
        _check("ocr_service", _check_ocr_service),
        _check("disk", _check_disk),
        _check("log_dir", _check_log_dir),
    ]
    if any(item["status"] == "fail" for item in checks):
        status = "fail"
    elif any(item["status"] in ("warn", "skip") for item in checks):
        status = "warn"
    else:
        status = "ok"
    return {
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config_name": config_name,
        "summary": {
            "pass": sum(1 for item in checks if item["status"] == "pass"),
            "warn": sum(1 for item in checks if item["status"] == "warn"),
            "fail": sum(1 for item in checks if item["status"] == "fail"),
            "skip": sum(1 for item in checks if item["status"] == "skip"),
        },
        "checks": checks,
    }
