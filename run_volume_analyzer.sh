#!/bin/bash
# 成交量分析批处理脚本 (Linux/macOS)
# 用法: ./run_volume_analyzer.sh [选项]

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 设置Python路径（根据实际情况修改）
PYTHON_CMD="python3"

# 设置日志目录
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# 设置日志文件
LOG_FILE="$LOG_DIR/volume_analyzer_$(date +%Y%m%d).log"

# 记录开始时间
echo "========================================" | tee -a "$LOG_FILE"
echo "成交量分析批处理 - $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 执行分析
$PYTHON_CMD src/volume_analyzer.py "$@" 2>&1 | tee -a "$LOG_FILE"

# 记录退出码
EXIT_CODE=$?

# 记录结束时间
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "批处理完成 - $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "退出码: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

exit $EXIT_CODE
