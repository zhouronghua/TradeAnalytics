#!/bin/bash

echo "===================================="
echo "     股票分析软件启动器"
echo "===================================="
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装Python 3.8或以上版本"
    exit 1
fi

echo "[信息] Python已安装"
python3 --version
echo ""

# 检查依赖包
echo "[检查] 正在检查依赖包..."
python3 -c "import akshare; import pandas; import numpy; import schedule" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[警告] 依赖包未完整安装"
    echo ""
    echo "是否现在安装依赖包？"
    echo "1. 是（使用国内镜像源，推荐）"
    echo "2. 是（使用默认源）"
    echo "3. 否，退出"
    echo ""
    read -p "请选择 [1/2/3]: " choice
    
    case $choice in
        1)
            echo "[安装] 正在安装依赖包..."
            pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
            if [ $? -ne 0 ]; then
                echo "[错误] 依赖包安装失败"
                exit 1
            fi
            ;;
        2)
            echo "[安装] 正在安装依赖包..."
            pip3 install -r requirements.txt
            if [ $? -ne 0 ]; then
                echo "[错误] 依赖包安装失败"
                exit 1
            fi
            ;;
        3)
            echo "[退出] 请手动安装依赖包后再运行"
            echo "安装命令: pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
            exit 0
            ;;
        *)
            echo "[错误] 无效的选择"
            exit 1
            ;;
    esac
fi

echo "[信息] 依赖包检查完成"
echo ""

# 启动程序
echo "[启动] 正在启动股票分析软件..."
echo ""
python3 main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序异常退出"
fi
