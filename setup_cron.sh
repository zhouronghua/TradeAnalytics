#!/bin/bash
#
# 设置 TradeAnalytics 定时任务
# 每个工作日 9:00, 12:00, 15:30 执行妖股筛选并发送邮件
#
# 用法: bash setup_cron.sh [install|remove|status]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON3="$(which python3)"
BATCH_SCRIPT="${SCRIPT_DIR}/batch_analyze.py"
LOG_DIR="${SCRIPT_DIR}/logs"
CRON_TAG="# TradeAnalytics-batch"

mkdir -p "$LOG_DIR"

show_usage() {
    echo "用法: $0 [install|remove|status]"
    echo ""
    echo "  install  - 安装定时任务(每工作日 9:00, 12:00, 15:30)"
    echo "  remove   - 移除定时任务"
    echo "  status   - 查看当前定时任务"
    echo ""
    echo "注意: 安装前请确保已在 config/config.ini 中配置:"
    echo "  1. [Email] auth_code = 你的QQ邮箱授权码"
    echo "  2. [DataSource] source = akshare 或 baostock"
}

install_cron() {
    echo "安装 TradeAnalytics 定时任务..."

    if [ ! -f "$BATCH_SCRIPT" ]; then
        echo "错误: 找不到 $BATCH_SCRIPT"
        exit 1
    fi

    if [ -z "$PYTHON3" ]; then
        echo "错误: 找不到 python3"
        exit 1
    fi

    # Remove old entries first
    remove_cron_quiet

    # Cron entries: weekdays only (1-5)
    # 9:00 - 盘前分析
    CRON_0900="0 9 * * 1-5 cd ${SCRIPT_DIR} && ${PYTHON3} ${BATCH_SCRIPT} >> ${LOG_DIR}/cron_0900.log 2>&1 ${CRON_TAG}"
    # 12:00 - 午休分析
    CRON_1200="0 12 * * 1-5 cd ${SCRIPT_DIR} && ${PYTHON3} ${BATCH_SCRIPT} >> ${LOG_DIR}/cron_1200.log 2>&1 ${CRON_TAG}"
    # 15:30 - 收盘后分析
    CRON_1530="30 15 * * 1-5 cd ${SCRIPT_DIR} && ${PYTHON3} ${BATCH_SCRIPT} >> ${LOG_DIR}/cron_1530.log 2>&1 ${CRON_TAG}"

    (crontab -l 2>/dev/null; echo "$CRON_0900"; echo "$CRON_1200"; echo "$CRON_1530") | crontab -

    echo "定时任务已安装:"
    echo "  工作日 09:00 - 盘前分析"
    echo "  工作日 12:00 - 午休分析"
    echo "  工作日 15:30 - 收盘后分析"
    echo ""
    echo "日志位置: ${LOG_DIR}/cron_*.log"
    echo ""

    show_status
}

remove_cron_quiet() {
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab -
}

remove_cron() {
    echo "移除 TradeAnalytics 定时任务..."
    remove_cron_quiet
    echo "已移除所有 TradeAnalytics 定时任务"
    echo ""
    show_status
}

show_status() {
    echo "当前 cron 任务:"
    local entries
    entries=$(crontab -l 2>/dev/null | grep "$CRON_TAG")
    if [ -z "$entries" ]; then
        echo "  (无 TradeAnalytics 任务)"
    else
        echo "$entries" | while IFS= read -r line; do
            echo "  $line"
        done
    fi
}

case "${1:-status}" in
    install)
        install_cron
        ;;
    remove)
        remove_cron
        ;;
    status)
        show_status
        ;;
    *)
        show_usage
        ;;
esac
