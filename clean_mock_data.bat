@echo off
chcp 65001 >nul
echo ====================================
echo      清理模拟数据
echo ====================================
echo.
echo 这将删除所有模拟数据文件
echo 包括：
echo   - data\daily\*.csv
echo   - data\stocks\*.csv
echo   - data\results\*.csv
echo.
echo 删除后可以运行 python main.py 下载真实数据
echo.

set /p choice=确定要删除吗？(Y/N): 

if /i "%choice%"=="Y" (
    echo.
    echo [删除] data\daily\*.csv
    del /q data\daily\*.csv 2>nul
    
    echo [删除] data\stocks\*.csv
    del /q data\stocks\*.csv 2>nul
    
    echo [删除] data\results\*.csv
    del /q data\results\*.csv 2>nul
    
    echo.
    echo [完成] 模拟数据已清理
    echo.
    echo 下一步：
    echo 1. 运行: python main.py
    echo 2. 点击"立即执行分析"
    echo 3. 等待真实数据下载完成
) else (
    echo.
    echo [取消] 未删除任何文件
)

echo.
pause
