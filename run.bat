@echo off
chcp 65001 >nul
echo ====================================
echo      股票分析软件启动器
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8或以上版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [信息] Python已安装
python --version
echo.

REM 检查依赖包
echo [检查] 正在检查依赖包...
python -c "import akshare; import pandas; import numpy; import schedule" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 依赖包未完整安装
    echo.
    echo 是否现在安装依赖包？
    echo 1. 是（使用国内镜像源，推荐）
    echo 2. 是（使用默认源）
    echo 3. 否，退出
    echo.
    set /p choice=请选择 [1/2/3]: 
    
    if "!choice!"=="1" (
        echo [安装] 正在安装依赖包...
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        if %errorlevel% neq 0 (
            echo [错误] 依赖包安装失败
            pause
            exit /b 1
        )
    ) else if "!choice!"=="2" (
        echo [安装] 正在安装依赖包...
        pip install -r requirements.txt
        if %errorlevel% neq 0 (
            echo [错误] 依赖包安装失败
            pause
            exit /b 1
        )
    ) else (
        echo [退出] 请手动安装依赖包后再运行
        echo 安装命令: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        pause
        exit /b 0
    )
)

echo [信息] 依赖包检查完成
echo.

REM 启动程序
echo [启动] 正在启动股票分析软件...
echo.
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序异常退出
    pause
)
