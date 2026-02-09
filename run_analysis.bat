@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM ========================================
REM TradeAnalytics 自动分析脚本
REM ========================================

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 创建日志目录
if not exist logs mkdir logs

REM 记录开始时间
echo. >> logs\scheduler.log
echo ======================================== >> logs\scheduler.log
echo [%date% %time%] 任务开始 >> logs\scheduler.log
echo ======================================== >> logs\scheduler.log

REM 检查Python环境
python --version >> logs\scheduler.log 2>&1
if errorlevel 1 (
    echo [ERROR] Python未安装或不在PATH中 >> logs\scheduler.log
    goto :error
)

REM 执行分析
echo [%date% %time%] 开始执行分析... >> logs\scheduler.log
python main.py >> logs\scheduler.log 2>&1

REM 检查执行结果
if errorlevel 1 (
    echo [%date% %time%] 分析失败，错误码: %errorlevel% >> logs\scheduler.log
    goto :error
) else (
    echo [%date% %time%] 分析成功完成 >> logs\scheduler.log
    goto :success
)

:error
echo [%date% %time%] 任务执行失败 >> logs\scheduler.log
exit /b 1

:success
echo [%date% %time%] 任务执行成功 >> logs\scheduler.log
exit /b 0
