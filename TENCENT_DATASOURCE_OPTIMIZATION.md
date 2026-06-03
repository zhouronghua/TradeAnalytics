# Tencent 数据源优化配置指南

## 概述

Tencent（腾讯财经）数据源相比其他数据源有以下优势：

- ✅ **支持多线程**：使用线程锁和限流控制，安全支持并发下载
- ✅ **速度快**：API响应速度快，适合首次下载大量数据
- ✅ **稳定性好**：有内置限流机制，避免被封IP
- ✅ **无需注册**：直接使用，无需token

## 推荐配置

### 基础配置（平衡性能和稳定性）

```ini
[DataSource]
source = tencent

[Download]
max_workers = 5          # 5个并发线程（推荐）
retry_times = 3          # 失败重试3次
retry_delay = 5          # 重试延迟5秒
daily_download_limit_mb = 0  # 首次运行无限制

[Analysis]
min_history_days = 150   # 最少150天历史数据
```

### 高速配置（首次下载，追求速度）

```ini
[DataSource]
source = tencent

[Download]
max_workers = 10         # 10个并发线程（快速）
retry_times = 3
retry_delay = 3          # 缩短重试延迟
daily_download_limit_mb = 0
```

### 极速配置（网络条件好）

```ini
[DataSource]
source = tencent

[Download]
max_workers = 20         # 20个并发线程（最快）
retry_times = 2          # 减少重试次数
retry_delay = 2
daily_download_limit_mb = 0
```

### 保守配置（网络不稳定）

```ini
[DataSource]
source = tencent

[Download]
max_workers = 3          # 3个并发线程（保守）
retry_times = 5          # 增加重试次数
retry_delay = 10         # 增加重试延迟
daily_download_limit_mb = 100
```

## 性能对比

基于 5000 只股票，150天历史数据的预估下载时间：

| 配置 | 并发数 | 预估时间 | 稳定性 | 适用场景 |
|------|--------|---------|--------|----------|
| 单线程 | 1 | ~4-5小时 | ⭐⭐⭐⭐⭐ | 极度保守 |
| 保守配置 | 3 | ~1.5-2小时 | ⭐⭐⭐⭐ | 网络不稳定 |
| 基础配置 | 5 | ~1小时 | ⭐⭐⭐⭐ | **推荐** |
| 高速配置 | 10 | ~30-40分钟 | ⭐⭐⭐ | 首次下载 |
| 极速配置 | 20 | ~20-30分钟 | ⭐⭐ | 网络条件好 |

注意：实际时间取决于网络速度和服务器响应速度。

## Tencent 数据源的限流机制

Tencent 数据源内置以下限流保护：

```python
# 每个请求最少间隔 0.3 秒
self._min_interval = 0.3

# 使用线程锁保证并发安全
self._request_lock = threading.Lock()
```

这意味着：
- **理论最大QPS**: 约 3-4 次/秒
- **多线程实际QPS**: 
  - 5线程: ~15-20 次/秒
  - 10线程: ~30-35 次/秒
  - 20线程: ~60-70 次/秒

## 首次运行建议

### 步骤1: 修改配置

编辑 `config/config.ini`：

```ini
[DataSource]
source = tencent

[Download]
max_workers = 10         # 首次下载使用10线程
retry_times = 3
retry_delay = 5
daily_download_limit_mb = 0  # 首次运行无限制
```

### 步骤2: 运行初始化

```bash
# 使用初始化脚本
python init_first_run.py

# 或直接运行
python src/volume_analyzer.py
```

### 步骤3: 后续运行优化

首次下载完成后，可以降低并发数：

```ini
[Download]
max_workers = 5          # 日常更新使用5线程足够
daily_download_limit_mb = 100  # 设置每日限制
```

## 性能优化技巧

### 1. 根据网络状况调整并发数

**网络良好**（下载速度 > 10MB/s）：
```ini
max_workers = 10-20
```

**网络一般**（下载速度 5-10MB/s）：
```ini
max_workers = 5-10
```

**网络较差**（下载速度 < 5MB/s）：
```ini
max_workers = 3-5
```

### 2. 监控下载进度

```bash
# 实时查看日志
tail -f logs/*.log | grep -E "进度|成功|失败"

# 统计已下载的文件数
watch -n 5 'ls data/stocks/*.csv | wc -l'

# 查看磁盘使用
watch -n 10 'du -sh data/stocks'
```

### 3. 处理下载失败

如果出现较多失败：

```bash
# 1. 降低并发数
[Download]
max_workers = 3  # 从10降到3

# 2. 增加重试次数和延迟
retry_times = 5
retry_delay = 10

# 3. 再次运行（会自动重试失败的股票）
python src/volume_analyzer.py
```

### 4. 分批下载（大数据量）

如果股票数量特别多（>10000只），可以分批下载：

```python
# 分批下载脚本
from src.data_downloader import DataDownloader
import pandas as pd

downloader = DataDownloader()
stock_list = downloader.download_stock_list()

# 每次下载1000只
batch_size = 1000
for i in range(0, len(stock_list), batch_size):
    batch = stock_list[i:i+batch_size]
    print(f"正在下载第 {i//batch_size + 1} 批，共 {len(batch)} 只股票")
    downloader.download_all_stocks(batch)
```

## 与其他数据源对比

### Tencent vs BaoStock

| 项目 | Tencent | BaoStock |
|------|---------|----------|
| 速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 多线程 | ✅ 支持 | ❌ 不建议 |
| 数据完整性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 稳定性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 注册要求 | ❌ 无需 | ❌ 无需 |
| 推荐并发数 | 5-10 | 1 |

**建议**：
- 首次下载：使用 Tencent（快速）
- 日常更新：使用 Tencent 或 BaoStock（都可以）
- 回测分析：使用 BaoStock（数据更完整）

### Tencent vs AkShare

| 项目 | Tencent | AkShare |
|------|---------|---------|
| 速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 多线程 | ✅ 支持 | ❌ 不建议 |
| 实时性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 稳定性 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 推荐并发数 | 5-10 | 1 |

**建议**：
- 历史数据：使用 Tencent（更快）
- 实时数据：使用 AkShare（更新更快）

## 常见问题

### Q1: Tencent 数据源支持的最大并发数是多少？

理论上可以设置很高（如50），但建议不超过20：
- **5-10线程**：最佳平衡
- **10-20线程**：追求速度
- **>20线程**：可能被限流或IP封禁

### Q2: 使用 Tencent 下载会被封IP吗？

不会，因为有内置限流保护：
- 每个请求间隔至少0.3秒
- 使用线程锁保证并发安全
- 建议并发数不超过20

### Q3: 首次下载5000只股票需要多久？

取决于配置：
- 5线程：约1小时
- 10线程：约30-40分钟
- 20线程：约20-30分钟

### Q4: 可以一边下载一边分析吗？

可以，但建议先完成首次下载：

```bash
# 首次完整下载
python init_first_run.py

# 之后正常运行
python src/volume_analyzer.py
```

### Q5: 下载过程中可以中断吗？

可以，按 Ctrl+C 中断：
- 已下载的数据会保存
- 再次运行会自动跳过已下载的股票
- 只下载缺失的股票

### Q6: Tencent 数据源的数据准确吗？

准确，但建议与其他数据源交叉验证：

```bash
# 同时使用多个数据源验证
[DataSource]
source = tencent  # 主数据源

# 定期用 BaoStock 验证关键股票
```

## 实战案例

### 案例1: 首次快速下载

```ini
# config/config.ini
[DataSource]
source = tencent

[Download]
max_workers = 10
daily_download_limit_mb = 0
```

```bash
# 运行下载
python init_first_run.py

# 预计30-40分钟完成
```

### 案例2: 日常更新（Crontab）

```ini
# config/config.ini
[DataSource]
source = tencent

[Download]
max_workers = 5  # 日常更新用5线程
daily_download_limit_mb = 100
```

```bash
# crontab 配置
30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
```

### 案例3: 网络不稳定环境

```ini
# config/config.ini
[DataSource]
source = tencent

[Download]
max_workers = 3  # 降低并发
retry_times = 5  # 增加重试
retry_delay = 10 # 增加延迟
```

## 总结

使用 Tencent 数据源的最佳实践：

1. ✅ **首次下载**：使用10线程，无下载限制
2. ✅ **日常更新**：使用5线程，设置100MB限制
3. ✅ **监控日志**：实时查看下载进度和错误
4. ✅ **处理失败**：降低并发数，增加重试
5. ✅ **网络优化**：根据网络状况调整并发数

推荐配置：

```ini
[DataSource]
source = tencent

[Download]
max_workers = 5          # 平衡性能和稳定性
retry_times = 3
retry_delay = 5
daily_download_limit_mb = 0  # 首次运行无限制，后续设为100
```

这样可以在保证稳定性的同时，获得最佳的下载速度！
