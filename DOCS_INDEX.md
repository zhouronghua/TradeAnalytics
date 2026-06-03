# TradeAnalytics 文档索引

## 快速开始

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [TENCENT_QUICKSTART.md](TENCENT_QUICKSTART.md) | Tencent数据源快速开始（推荐） | 想快速开始的用户 |
| [VOLUME_ANALYZER_QUICKSTART.md](VOLUME_ANALYZER_QUICKSTART.md) | Volume Analyzer 完整指南 | 所有用户 |
| [SUMMARY_DATA_FRESHNESS.md](SUMMARY_DATA_FRESHNESS.md) | 数据时效性改进快速总结 | **推荐阅读** |
| [FIXED_ISSUES.md](FIXED_ISSUES.md) | 常见问题修复说明 | 遇到问题的用户 |

## 配置和设置

| 文档 | 说明 | 适合人群 |
|------|------|----------|
| [crontab_setup.md](crontab_setup.md) | Crontab 定时任务详细配置 | Linux/macOS 用户 |
| [crontab.example](crontab.example) | Crontab 配置示例 | 需要参考示例的用户 |
| [TENCENT_DATASOURCE_OPTIMIZATION.md](TENCENT_DATASOURCE_OPTIMIZATION.md) | Tencent 数据源优化指南 | 追求性能的用户 |

## 脚本和工具

| 文件 | 说明 | 用途 |
|------|------|------|
| `setup_tencent.py` | Tencent 数据源快速配置 | 一键配置 Tencent |
| `init_first_run.py` | 首次运行初始化脚本 | 自动下载数据 |
| `test_batch_setup.py` | 批处理配置测试 | 验证配置正确性 |
| `test_data_freshness.py` | 数据时效性测试 | 验证只推送最近数据 |
| `run_volume_analyzer.sh` | Linux/macOS 运行脚本 | 封装运行命令 |
| `run_volume_analyzer.bat` | Windows 运行脚本 | 封装运行命令 |

## 更新日志

| 文档 | 说明 |
|------|------|
| [VOLUME_ANALYZER_CHANGELOG.md](VOLUME_ANALYZER_CHANGELOG.md) | Volume Analyzer 更新日志 |
| [DATA_FRESHNESS_UPDATE.md](DATA_FRESHNESS_UPDATE.md) | 数据时效性改进说明（2026-06-03） |

## 按使用场景查找文档

### 场景1: 我是新手，想快速开始

1. 阅读 [TENCENT_QUICKSTART.md](TENCENT_QUICKSTART.md)
2. 运行 `python setup_tencent.py`
3. 运行 `python init_first_run.py`
4. 完成！

### 场景2: 我想使用 Tencent 数据源加速下载

1. 阅读 [TENCENT_DATASOURCE_OPTIMIZATION.md](TENCENT_DATASOURCE_OPTIMIZATION.md)
2. 运行 `python setup_tencent.py`
3. 选择合适的配置方案

### 场景3: 我想添加到 Crontab 定时任务

1. 完成首次下载（参考场景1）
2. 阅读 [crontab_setup.md](crontab_setup.md)
3. 参考 [crontab.example](crontab.example)
4. 配置 crontab

### 场景4: 我遇到了问题

1. 阅读 [FIXED_ISSUES.md](FIXED_ISSUES.md)
2. 运行 `python test_batch_setup.py` 诊断问题
3. 查看日志 `tail -f logs/*.log`

### 场景5: 我想优化性能

1. 阅读 [TENCENT_DATASOURCE_OPTIMIZATION.md](TENCENT_DATASOURCE_OPTIMIZATION.md)
2. 根据网络条件调整并发数
3. 监控下载进度和成功率

### 场景6: 我想了解完整功能

1. 阅读 [VOLUME_ANALYZER_QUICKSTART.md](VOLUME_ANALYZER_QUICKSTART.md)
2. 阅读 [VOLUME_ANALYZER_CHANGELOG.md](VOLUME_ANALYZER_CHANGELOG.md)

### 场景7: 我想确保只推送最新数据

1. 阅读 [SUMMARY_DATA_FRESHNESS.md](SUMMARY_DATA_FRESHNESS.md)
2. 运行 `python test_data_freshness.py` 测试
3. 查看详细文档 [DATA_FRESHNESS_UPDATE.md](DATA_FRESHNESS_UPDATE.md)

## 命令速查

### 配置和初始化

```bash
# 快速配置 Tencent 数据源
python setup_tencent.py

# 首次下载数据
python init_first_run.py

# 测试配置
python test_batch_setup.py
```

### 运行分析

```bash
# 完整运行（更新数据+分析+推送）
python src/volume_analyzer.py

# 只分析（不更新数据）
python src/volume_analyzer.py --no-update

# 不发送通知
python src/volume_analyzer.py --no-email --no-notification

# 使用封装脚本
./run_volume_analyzer.sh          # Linux/macOS
run_volume_analyzer.bat            # Windows
```

### 测试功能

```bash
# 测试邮件
python -c "from src.email_sender import EmailSender; EmailSender().send_test()"

# 测试方糖推送
python -c "from src.notification import NotificationService; NotificationService().send_test_message()"

# 测试数据下载
python -c "from src.data_downloader import DataDownloader; d=DataDownloader(); print(d.download_stock_list())"
```

### 查看日志和结果

```bash
# 实时查看日志
tail -f logs/*.log

# 查看最新结果
ls -lh data/results/

# 统计已下载股票数
ls data/stocks/*.csv | wc -l

# 查看磁盘使用
du -sh data/
```

## 配置文件说明

### config/config.ini

主配置文件，包含所有配置项：

```ini
[Paths]          # 路径配置
[DataSource]     # 数据源配置
[Analysis]       # 分析参数
[Scheduler]      # 定时任务
[Download]       # 下载配置
[Email]          # 邮件推送
[Notification]   # 方糖推送
```

详细说明请查看 `config/config.ini.example`

## 数据源对比

| 数据源 | 速度 | 多线程 | 稳定性 | 推荐并发数 | 特点 |
|--------|------|--------|--------|-----------|------|
| **tencent** | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐ | 5-10 | 快速，推荐首次下载 |
| baostock | ⭐⭐⭐ | ❌ | ⭐⭐⭐⭐⭐ | 1 | 稳定，数据完整 |
| akshare | ⭐⭐⭐⭐ | ❌ | ⭐⭐⭐ | 1 | 实时性好 |
| tushare | ⭐⭐⭐⭐ | ❌ | ⭐⭐⭐⭐ | 1 | 需要token |

## 推荐配置组合

### 新手推荐（快速开始）

```ini
[DataSource]
source = tencent

[Download]
max_workers = 10
daily_download_limit_mb = 0
```

**优点**：30-40分钟完成首次下载

### 日常推荐（定时任务）

```ini
[DataSource]
source = tencent

[Download]
max_workers = 5
daily_download_limit_mb = 100
```

**优点**：平衡性能和稳定性

### 回测推荐（数据完整性）

```ini
[DataSource]
source = baostock

[Download]
max_workers = 1

[Analysis]
min_history_days = 365
```

**优点**：数据最完整，适合历史回测

## 常见问题快速链接

- [数据更新失败怎么办？](FIXED_ISSUES.md#q2-数据更新失败怎么办)
- [找不到股票数据文件？](FIXED_ISSUES.md#q2-数据未下载)
- [如何提高下载速度？](TENCENT_DATASOURCE_OPTIMIZATION.md#性能对比)
- [Crontab 执行失败？](VOLUME_ANALYZER_QUICKSTART.md#q4-crontab-执行失败怎么办)
- [邮件发送失败？](VOLUME_ANALYZER_QUICKSTART.md#q1-如何获取-qq-邮箱授权码)
- [方糖推送不工作？](VOLUME_ANALYZER_QUICKSTART.md#q2-如何获取方糖-sendkey)

## 获取帮助

### 查看命令行帮助

```bash
python src/volume_analyzer.py --help
python test_batch_setup.py --help
python init_first_run.py --help
python setup_tencent.py --help
```

### 查看日志

```bash
# 查看所有日志
tail -f logs/*.log

# 只查看错误
grep ERROR logs/*.log

# 按时间查看
ls -lt logs/
```

### 诊断工具

```bash
# 运行完整测试
python test_batch_setup.py

# 检查配置
python -c "from src.utils import Config; c=Config(); print(dict(c.items()))"

# 检查数据
ls -lh data/stocks/ | head -20
```

## 贡献和反馈

如果发现文档有误或需要补充，欢迎反馈！

## 文档更新历史

- 2026-06-01: 添加 Tencent 数据源支持和优化文档
- 2026-06-01: 添加批处理功能和 Crontab 支持
- 2026-06-01: 创建文档索引
