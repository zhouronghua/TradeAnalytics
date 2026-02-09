@echo off
chcp 65001 > nul
echo.
echo ========================================
echo 检查 TradeAnalytics 定时任务状态
echo ========================================
echo.

REM 检查任务是否存在
schtasks /query /tn "TradeAnalytics 股票分析" > nul 2>&1
if errorlevel 1 (
    echo [X] 任务不存在
    echo.
    echo 请先创建任务：
    echo 1. 按Win+R，输入 taskschd.msc
    echo 2. 创建基本任务
    echo 3. 参考 WINDOWS_SCHEDULER_SETUP.md
    echo.
    goto :end
) else (
    echo [√] 任务已创建
    echo.
)

REM 显示任务详情
echo 任务详情:
echo ----------------------------------------
schtasks /query /tn "TradeAnalytics 股票分析" /fo LIST /v | findstr /C:"任务名" /C:"状态" /C:"上次运行时间" /C:"下次运行时间" /C:"上次运行结果"

echo.
echo ========================================
echo 最近的执行日志:
echo ========================================
if exist logs\scheduler.log (
    echo.
    type logs\scheduler.log | more
) else (
    echo [提示] 日志文件不存在: logs\scheduler.log
)

:end
echo.
pause
