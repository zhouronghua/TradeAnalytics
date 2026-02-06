@echo off
chcp 65001 >nul
echo ========================================
echo 完整清理和重置系统
echo ========================================
echo.

REM 1. 停止所有Python进程
echo [1/5] 停止所有Python进程...
taskkill /F /IM python.exe /T >nul 2>&1
if %errorlevel%==0 (
    echo [OK] 已停止Python进程
) else (
    echo [INFO] 没有运行中的Python进程
)
timeout /t 2 /nobreak >nul

REM 2. 删除所有旧的股票数据
echo.
echo [2/5] 删除旧的股票数据...
if exist "data\daily\*.csv" (
    del /Q "data\daily\*.csv" >nul 2>&1
    echo [OK] 已删除 data\daily\ 中的所有CSV文件
) else (
    echo [INFO] data\daily\ 目录为空
)

REM 3. 删除股票列表缓存
echo.
echo [3/5] 删除股票列表缓存...
if exist "data\stocks\stock_list.csv" (
    del /Q "data\stocks\stock_list.csv" >nul 2>&1
    echo [OK] 已删除股票列表缓存
) else (
    echo [INFO] 没有股票列表缓存
)

REM 4. 删除结果文件
echo.
echo [4/5] 删除旧的分析结果...
if exist "data\results\*.csv" (
    del /Q "data\results\*.csv" >nul 2>&1
    echo [OK] 已删除旧的分析结果
) else (
    echo [INFO] 没有分析结果文件
)

REM 5. 验证配置
echo.
echo [5/5] 验证配置文件...
findstr /C:"source = baostock" config\config.ini >nul
if %errorlevel%==0 (
    echo [OK] 配置文件正确，使用BaoStock数据源
) else (
    echo [WARNING] 配置文件可能不正确
    echo 请检查 config\config.ini 中 [DataSource] 的 source 设置
)

echo.
echo ========================================
echo 清理完成
echo ========================================
echo.
echo 当前配置:
echo - 数据源: BaoStock
echo - 所有旧数据已删除
echo - 准备重新下载
echo.
echo 下一步操作:
echo 1. 运行: python main.py
echo 2. 或运行: run.bat
echo.
echo 程序会使用BaoStock下载正确的数据
echo 预计需要时间: 20-30分钟（取决于网速）
echo.
pause
