@echo off
REM ========================================
REM TradeAnalytics 后台启动脚本
REM ========================================

cd /d "%~dp0"

REM 创建日志目录
if not exist logs mkdir logs

REM 记录启动时间
echo [%date% %time%] TradeAnalytics 后台启动 >> logs\startup.log

REM 隐藏窗口运行（最小化）
start /min "" python main.py

echo.
echo ============================================
echo TradeAnalytics 已在后台启动
echo 程序将在每天15:30自动执行分析
echo 分析结果将推送到您的微信
echo ============================================
echo.
echo 查看日志: logs\task_scheduler.log
echo 查看启动日志: logs\startup.log
echo.
timeout /t 5
