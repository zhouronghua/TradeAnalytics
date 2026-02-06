#!/bin/bash

echo "===================================="
echo "     清理模拟数据"
echo "===================================="
echo ""
echo "这将删除所有模拟数据文件"
echo "包括："
echo "  - data/daily/*.csv"
echo "  - data/stocks/*.csv"
echo "  - data/results/*.csv"
echo ""
echo "删除后可以运行 python main.py 下载真实数据"
echo ""

read -p "确定要删除吗？(y/n): " choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo ""
    echo "[删除] data/daily/*.csv"
    rm -f data/daily/*.csv 2>/dev/null
    
    echo "[删除] data/stocks/*.csv"
    rm -f data/stocks/*.csv 2>/dev/null
    
    echo "[删除] data/results/*.csv"
    rm -f data/results/*.csv 2>/dev/null
    
    echo ""
    echo "[完成] 模拟数据已清理"
    echo ""
    echo "下一步："
    echo "1. 运行: python main.py"
    echo "2. 点击'立即执行分析'"
    echo "3. 等待真实数据下载完成"
else
    echo ""
    echo "[取消] 未删除任何文件"
fi
