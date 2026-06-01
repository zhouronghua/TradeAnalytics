# Volume Analyzer Crontab 配置指南

## 功能说明

`volume_analyzer.py` 现已支持完整的批处理功能，包括：
- 自动更新交易数据
- 成交量暴涨分析（当天成交量>=前7天平均成交量5倍，且收盘价>均线）
- 邮件推送分析结果
- 方糖（Server酱）推送消息

## 使用方式

### 1. 命令行直接运行

```bash
# 完整运行（更新数据+分析+推送）
cd /path/to/TradeAnalytics
python src/volume_analyzer.py

# 只分析，不更新数据
python src/volume_analyzer.py --no-update

# 只分析，不发送任何通知
python src/volume_analyzer.py --no-email --no-notification

# 指定配置文件
python src/volume_analyzer.py --config config/custom.ini
```

### 2. 添加到 Crontab

#### Linux/macOS 配置步骤

1. 编辑 crontab：
```bash
crontab -e
```

2. 添加定时任务（示例）：

```bash
# 每个交易日下午3点30分执行成交量分析
30 15 * * 1-5 cd /path/to/TradeAnalytics && /usr/bin/python3 src/volume_analyzer.py >> logs/volume_analyzer.log 2>&1

# 每天下午3点执行（包括周末，脚本内会判断交易日）
0 15 * * * cd /path/to/TradeAnalytics && /usr/bin/python3 src/volume_analyzer.py >> logs/volume_analyzer.log 2>&1

# 每天收盘后执行，只分析不更新数据（数据由其他任务更新）
30 15 * * 1-5 cd /path/to/TradeAnalytics && /usr/bin/python3 src/volume_analyzer.py --no-update >> logs/volume_analyzer.log 2>&1
```

#### Windows 任务计划程序配置

1. 创建批处理文件 `run_volume_analyzer.bat`：

```batch
@echo off
cd /d E:\code\TradeAnalytics
python src\volume_analyzer.py >> logs\volume_analyzer.log 2>&1
```

2. 打开任务计划程序：
   - 按 `Win + R`，输入 `taskschd.msc`
   - 创建基本任务
   - 名称：`TradeAnalytics - Volume Analyzer`
   - 触发器：每天下午3:30
   - 操作：启动程序
   - 程序/脚本：`E:\code\TradeAnalytics\run_volume_analyzer.bat`

## Crontab 时间格式说明

```
分钟 小时 日 月 星期 命令
*    *   *  *  *    command
```

示例：
- `30 15 * * 1-5` - 每周一到周五下午3:30
- `0 16 * * *` - 每天下午4:00
- `*/30 9-15 * * 1-5` - 交易日每30分钟执行一次（9:00-15:00）

## 配置要求

### 1. 基础配置（config/config.ini）

必须配置以下参数：

```ini
[Paths]
data_dir = ./data
stocks_dir = ./data/stocks
results_dir = ./data/results

[DataSource]
source = baostock
update_stock_list_days = 1

[Analysis]
ma_period = 20
volume_ratio_threshold = 5.0
min_history_days = 30

[Download]
max_workers = 1
```

### 2. 邮件推送配置（可选）

```ini
[Email]
enabled = true
smtp_server = smtp.qq.com
smtp_port = 465
smtp_ssl = true
sender_email = your_email@qq.com
sender_name = TradeAnalytics
auth_code = your_qq_auth_code
receiver_emails = receiver1@qq.com,receiver2@qq.com
```

QQ邮箱授权码获取：
1. 登录QQ邮箱
2. 设置 -> 账户 -> POP3/SMTP服务
3. 开启服务并获取授权码

### 3. 方糖推送配置（可选）

```ini
[Notification]
enabled = true
push_type = serverchan
serverchan_key = your_serverchan_key
push_history_days = 3
push_max_stocks = 20
```

方糖（Server酱）配置：
1. 访问 https://sct.ftqq.com/
2. 使用微信扫码登录
3. 获取 SendKey
4. 填入配置文件

## 日志查看

```bash
# 查看最新日志
tail -f logs/volume_analyzer.log

# 查看今天的日志
tail -n 100 logs/volume_analyzer.log

# 查看错误日志
grep ERROR logs/volume_analyzer.log
```

## 常见问题

### 1. Crontab 执行失败

检查项：
- Python 路径是否正确（使用 `which python3` 查看）
- 工作目录是否正确
- 配置文件路径是否存在
- 日志目录权限是否正确

### 2. 数据更新失败

检查项：
- 网络连接是否正常
- BaoStock 服务是否可用
- 数据目录是否有写权限

### 3. 邮件发送失败

检查项：
- SMTP 配置是否正确
- 授权码是否正确（不是QQ密码）
- 收件人邮箱格式是否正确

### 4. 方糖推送失败

检查项：
- SendKey 是否正确
- 网络连接是否正常
- 是否超过每日推送限制

## 性能优化建议

1. **分离数据更新和分析**

如果数据量大，可以分开执行：

```bash
# 上午更新数据
0 9 * * 1-5 cd /path/to/TradeAnalytics && python src/data_downloader.py

# 下午分析数据（不更新）
30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py --no-update
```

2. **限制下载量**

在 config.ini 中设置：
```ini
[Download]
daily_download_limit_mb = 100
```

3. **使用历史数据**

首次运行后，后续只需增量更新：
```bash
python src/volume_analyzer.py --no-update
```

## 安全建议

1. **敏感信息使用环境变量**

```bash
# 在 ~/.bashrc 或 crontab 中设置
export TA_EMAIL_SENDER=your_email@qq.com
export TA_EMAIL_AUTH=your_auth_code
export TA_SERVERCHAN_KEY=your_sendkey
```

2. **配置文件权限**

```bash
chmod 600 config/config.ini
```

3. **日志轮转**

创建 `/etc/logrotate.d/tradeanalytics`：
```
/path/to/TradeAnalytics/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
```

## 测试建议

在添加到 crontab 前，先手动测试：

```bash
# 测试完整流程
python src/volume_analyzer.py

# 测试邮件配置
python -c "from src.email_sender import EmailSender; EmailSender().send_test()"

# 测试方糖推送
python -c "from src.notification import NotificationService; NotificationService().send_test_message()"
```

## 维护建议

1. 定期检查日志
2. 定期清理旧数据
3. 定期更新依赖包
4. 监控磁盘空间
5. 备份配置文件
