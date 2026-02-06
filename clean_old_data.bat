@echo off
chcp 65001 >nul
echo ========================================
echo 清理旧股票数据
echo ========================================
echo.
echo 这将删除所有旧的股票数据文件
echo 下次运行时会用BaoStock重新下载正确的数据
echo.
echo 即将删除:
echo - data\daily\*.csv （所有股票历史数据）
echo - data\stocks\stock_list.csv （股票列表缓存）
echo.
pause

echo.
echo 开始清理...

if exist "data\daily\*.csv" (
    del /Q "data\daily\*.csv"
    echo [OK] 已删除旧的股票历史数据
) else (
    echo [INFO] 没有找到股票历史数据文件
)

if exist "data\stocks\stock_list.csv" (
    del /Q "data\stocks\stock_list.csv"
    echo [OK] 已删除股票列表缓存
) else (
    echo [INFO] 没有找到股票列表缓存
)

echo.
echo ========================================
echo 清理完成
echo ========================================
echo.
echo 下一步: 运行 python main.py 或 run.bat
echo 程序会使用BaoStock重新下载正确的数据
echo.
pause
