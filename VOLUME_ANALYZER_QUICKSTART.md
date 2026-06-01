# Volume Analyzer 快速开始指南

## 功能概述

`volume_analyzer.py` 是一个完整的批处理工具，具备以下功能：

1. 自动更新股票交易数据
2. 分析成交量暴涨股票（规则：当天成交量 >= 前7天平均成交量 5倍，且收盘价 > 均线）
3. 自动发送邮件报告
4. 自动发送方糖（Server酱）推送
5. 支持命令行参数配置
6. 适合添加到 crontab 定时任务

## 快速开始

### 第一步：配置文件

```bash
# 复制配置示例
cp config/config.ini.example config/config.ini

# 编辑配置文件
vim config/config.ini  # 或使用其他编辑器
```

必须配置的项：

```ini
[Analysis]
ma_period = 20                    # 均线周期
volume_ratio_threshold = 5.0      # 成交量倍数阈值

[DataSource]
source = baostock                 # 数据源（推荐 baostock）
```

可选配置（邮件推送）：

```ini
[Email]
enabled = true
sender_email = your_email@qq.com
auth_code = your_qq_auth_code     # QQ邮箱授权码
receiver_emails = receiver@qq.com
```

可选配置（方糖推送）：

```ini
[Notification]
enabled = true
push_type = serverchan
serverchan_key = your_sendkey     # 从 https://sct.ftqq.com/ 获取
```

### 第二步：测试配置

```bash
# 运行配置测试脚本
python test_batch_setup.py
```

测试会检查：
- 配置文件是否正确
- 目录结构是否完整
- 数据源是否可用
- 邮件配置是否正确
- 方糖推送是否正常

### 第三步：首次运行

```bash
# 完整运行（更新数据 + 分析 + 推送）
python src/volume_analyzer.py

# 或使用封装脚本（推荐）
./run_volume_analyzer.sh          # Linux/macOS
run_volume_analyzer.bat            # Windows
```

命令行参数：

```bash
# 不更新数据，使用现有数据
python src/volume_analyzer.py --no-update

# 不发送邮件
python src/volume_analyzer.py --no-email

# 不发送推送
python src/volume_analyzer.py --no-notification

# 组合使用：只分析，不推送
python src/volume_analyzer.py --no-email --no-notification
```

### 第四步：添加到 Crontab（定时任务）

#### Linux/macOS

```bash
# 1. 给脚本添加执行权限
chmod +x run_volume_analyzer.sh

# 2. 编辑 crontab
crontab -e

# 3. 添加定时任务（每个交易日下午3:30执行）
30 15 * * 1-5 /path/to/TradeAnalytics/run_volume_analyzer.sh

# 4. 保存退出，查看当前配置
crontab -l
```

#### Windows 任务计划程序

1. 打开任务计划程序：`Win + R` -> 输入 `taskschd.msc`
2. 创建基本任务：
   - 名称：`TradeAnalytics - Volume Analyzer`
   - 触发器：每天下午3:30
   - 操作：启动程序
   - 程序：`E:\code\TradeAnalytics\run_volume_analyzer.bat`

## 使用场景

### 场景1：完全自动化（推荐）

每天自动更新数据、分析并推送结果

```bash
# Crontab 配置
30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
```

### 场景2：分离数据更新和分析

数据量大时，分开执行可提高效率

```bash
# 上午9:00 更新数据
0 9 * * 1-5 cd /path/to/TradeAnalytics && python -m src.data_downloader

# 下午3:30 分析数据（不更新）
30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py --no-update
```

### 场景3：手动分析

需要手动触发分析时

```bash
# 使用现有数据分析
python src/volume_analyzer.py --no-update

# 完整分析（更新数据）
python src/volume_analyzer.py
```

### 场景4：测试模式

测试配置但不发送通知

```bash
python src/volume_analyzer.py --no-email --no-notification
```

## 输出说明

### 终端输出

```
============================================================
开始批处理成交量分析
============================================================

[步骤1/3] 更新交易数据...
数据更新成功: 总计5000, 失败0

[步骤2/3] 分析成交量暴涨股票...
找到 5000 个股票数据文件
找到 15 只符合条件的股票
结果已保存: ./data/results/volume_analysis_20240601_153000.csv

[步骤3/3] 发送分析结果...
邮件发送成功
方糖推送成功

============================================================
批处理分析完成! 找到 15 只符合条件的股票
============================================================
```

### 结果文件

CSV 格式，保存在 `data/results/` 目录：

```csv
stock_code,stock_name,date,close,ma,ma_period,volume,avg_7day_volume,volume_ratio,price_above_ma,data_latest_date
600000,浦发银行,2024-06-01,10.50,10.20,20,5000000,800000,6.25,2.94,2024-06-01
...
```

### 邮件/推送内容

包含：
- 分析日期
- 符合条件的股票数量
- 近3日趋势对比
- 股票详细信息（代码、名称、收盘价、均线、成交量倍数）

## 常见问题

### Q1: 如何获取 QQ 邮箱授权码？

1. 登录 QQ 邮箱
2. 设置 -> 账户 -> POP3/SMTP服务
3. 开启服务
4. 生成授权码（不是QQ密码）

### Q2: 如何获取方糖 SendKey？

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制 SendKey

### Q3: 找不到符合条件的股票怎么办？

可能原因：
- 当天市场没有符合条件的股票
- 数据未更新或数据不完整
- 阈值设置过高

解决方法：
- 降低阈值（修改 `config.ini` 中的 `volume_ratio_threshold`）
- 确保数据已更新（运行 `python src/volume_analyzer.py`）

### Q4: Crontab 执行失败怎么办？

检查清单：
- [ ] Python 路径是否正确（`which python3`）
- [ ] 工作目录是否正确
- [ ] 配置文件是否存在
- [ ] 日志目录是否有写权限
- [ ] cron 服务是否运行（`systemctl status cron`）

查看日志：
```bash
tail -f logs/volume_analyzer.log
```

### Q5: 数据更新失败怎么办？

检查清单：
- [ ] 网络连接是否正常
- [ ] BaoStock 服务是否可用
- [ ] 数据目录是否有写权限
- [ ] 是否超过下载限制

临时解决：
```bash
# 跳过数据更新，使用现有数据
python src/volume_analyzer.py --no-update
```

### Q6: 如何修改分析规则？

编辑 `config/config.ini`：

```ini
[Analysis]
ma_period = 30                    # 改为30日均线
volume_ratio_threshold = 3.0      # 改为3倍成交量
```

## 性能优化

### 1. 使用增量更新

首次运行后，后续可使用 `--no-update` 跳过数据更新

```bash
python src/volume_analyzer.py --no-update
```

### 2. 限制下载量

在 `config.ini` 中设置：

```ini
[Download]
daily_download_limit_mb = 100     # 每日下载限制（MB）
```

### 3. 调整并发数

在 `config.ini` 中设置：

```ini
[Download]
max_workers = 1                   # 建议使用单线程，避免被限流
```

## 日志管理

### 查看日志

```bash
# 实时查看
tail -f logs/volume_analyzer.log

# 查看最近100行
tail -n 100 logs/volume_analyzer.log

# 查看错误日志
grep ERROR logs/volume_analyzer.log

# 按日期查看
ls -lh logs/volume_analyzer*.log
```

### 日志轮转（推荐）

创建 `/etc/logrotate.d/tradeanalytics`：

```
/path/to/TradeAnalytics/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    copytruncate
}
```

手动执行轮转：
```bash
logrotate -f /etc/logrotate.d/tradeanalytics
```

## 安全建议

### 1. 保护敏感信息

使用环境变量而非配置文件：

```bash
# 在 ~/.bashrc 中设置
export TA_EMAIL_SENDER=your_email@qq.com
export TA_EMAIL_AUTH=your_auth_code
export TA_SERVERCHAN_KEY=your_sendkey
```

### 2. 限制配置文件权限

```bash
chmod 600 config/config.ini
```

### 3. 定期更新依赖

```bash
pip install --upgrade akshare baostock tushare
```

## 监控和维护

### 1. 定期检查日志

```bash
# 每周检查一次
grep -i error logs/volume_analyzer.log | tail -n 50
```

### 2. 监控磁盘空间

```bash
du -sh data/
df -h
```

### 3. 清理旧数据

```bash
# 清理30天前的结果文件
find data/results/ -name "*.csv" -mtime +30 -delete

# 清理30天前的日志
find logs/ -name "*.log" -mtime +30 -delete
```

### 4. 备份配置

```bash
# 定期备份配置文件
cp config/config.ini config/config.ini.backup.$(date +%Y%m%d)
```

## 获取帮助

```bash
# 查看命令行帮助
python src/volume_analyzer.py --help

# 运行测试脚本
python test_batch_setup.py

# 查看详细文档
cat crontab_setup.md
```

## 相关文档

- `crontab_setup.md` - Crontab 详细配置指南
- `crontab.example` - Crontab 配置示例
- `test_batch_setup.py` - 配置测试脚本
- `config/config.ini.example` - 配置文件示例
