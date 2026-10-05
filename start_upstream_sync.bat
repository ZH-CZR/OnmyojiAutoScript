@echo off
chcp 65001 >nul
title 上游提交同步工具
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul || set "PY=py"

echo ==================================================
echo   上游提交同步工具
echo   浏览器会自动打开；关闭本窗口即停止服务
echo ==================================================
echo.
%PY% dev_tools\upstream_sync_web.py
echo.
echo 服务已退出。按任意键关闭窗口。
pause >nul