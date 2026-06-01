@echo off
REM 成交量分析批处理脚本 (Windows)
REM 用法: run_volume_analyzer.bat [选项]

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 设置Python路径（根据实际情况修改）
set PYTHON_CMD=python

REM 设置日志目录
set LOG_DIR=.\logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 设置日志文件
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
set LOG_FILE=%LOG_DIR%\volume_analyzer_%mydate%.log

REM 记录开始时间
echo ======================================== >> "%LOG_FILE%"
echo 成交量分析批处理 - %date% %time% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"
echo.

REM 执行分析
%PYTHON_CMD% src\volume_analyzer.py %* 2>&1 | tee -a "%LOG_FILE%"

REM 记录结束时间
echo. >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"
echo 批处理完成 - %date% %time% >> "%LOG_FILE%"
echo 退出码: %ERRORLEVEL% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

exit /b %ERRORLEVEL%
