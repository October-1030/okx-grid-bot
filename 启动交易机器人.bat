@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ========================================
echo    智能量化系统 - 启动交易
echo ========================================
echo.
echo 注意: 请确保已配置好 .env 文件中的 API Key
echo 按 Ctrl+C 可以安全停止机器人
echo.
pause
python smart_bot.py
echo.
echo ========================================
echo    机器人已停止，按任意键关闭窗口
echo ========================================
pause >nul
