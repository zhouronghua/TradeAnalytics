# Tencent 数据源快速开始

## 为什么选择 Tencent 数据源？

✅ **速度快** - 首次下载5000只股票只需30-40分钟（10线程）  
✅ **支持多线程** - 安全并发，内置限流保护  
✅ **无需注册** - 直接使用，无需token  
✅ **稳定可靠** - 腾讯财经官方API  

## 一键配置

```bash
# 运行快速配置脚本
python setup_tencent.py

# 选择 "1. 首次下载（快速）"
# 然后运行
python init_first_run.py
```

就这么简单！

## 手动配置

### 步骤1: 修改配置文件

编辑 `config/config.ini`（如果不存在，复制 `config.ini.example`）：

```ini
[DataSource]
source = tencent

[Download]
max_workers = 10         # 首次下载用10线程
daily_download_limit_mb = 0
```

### 步骤2: 首次下载

```bash
python init_first_run.py
```

预计时间：30-40分钟（5000只股票）

### 步骤3: 运行分析

```bash
python src/volume_analyzer.py --no-update
```

## 配置方案对比

| 方案 | 线程数 | 下载时间 | 适用场景 |
|------|--------|----------|----------|
| 首次快速 | 10 | ~30-40分钟 | 首次下载 |
| 日常使用 | 5 | - | 定时任务 |
| 保守稳定 | 3 | ~1.5-2小时 | 网络不稳定 |

## 性能对比

### Tencent vs 其他数据源

**首次下载5000只股票对比**：

| 数据源 | 并发数 | 预计时间 |
|--------|--------|----------|
| Tencent | 10 | 30-40分钟 ⭐⭐⭐⭐⭐ |
| Tencent | 5 | 1小时 ⭐⭐⭐⭐ |
| BaoStock | 1 | 4-5小时 ⭐⭐⭐ |
| AkShare | 1 | 3-4小时 ⭐⭐⭐ |

## 三种配置方案详解

### 方案1: 首次快速下载（推荐）

```ini
[DataSource]
source = tencent

[Download]
max_workers = 10
retry_times = 3
retry_delay = 5
daily_download_limit_mb = 0
```

**适合**：
- 首次下载
- 需要快速获取历史数据
- 网络条件良好

**预计时间**：30-40分钟

### 方案2: 日常使用

```ini
[DataSource]
source = tencent

[Download]
max_workers = 5
retry_times = 3
retry_delay = 5
daily_download_limit_mb = 100
```

**适合**：
- 日常定时更新
- Crontab 定时任务
- 平衡性能和资源占用

**Crontab 配置**：
```bash
30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
```

### 方案3: 保守稳定

```ini
[DataSource]
source = tencent

[Download]
max_workers = 3
retry_times = 5
retry_delay = 10
daily_download_limit_mb = 100
```

**适合**：
- 网络不稳定
- 带宽有限
- 避免频繁失败

## 常见问题

### Q: 为什么 Tencent 可以多线程？

A: Tencent 数据源内置了线程锁和限流控制：
```python
# 每个请求最少间隔 0.3 秒
self._min_interval = 0.3
self._request_lock = threading.Lock()
```

### Q: 最大可以用多少线程？

A: 理论上可以很高，但建议：
- **5线程** - 日常使用推荐
- **10线程** - 首次下载推荐
- **20线程** - 极限速度（不推荐）

### Q: 会被封IP吗？

A: 不会，因为有限流保护。建议不超过20线程。

### Q: 下载到一半中断了怎么办？

A: 再次运行会自动跳过已下载的股票：
```bash
python init_first_run.py
```

### Q: 如何查看下载进度？

```bash
# 实时查看日志
tail -f logs/*.log | grep "进度"

# 统计已下载文件数
watch -n 5 'ls data/stocks/*.csv | wc -l'
```

## 完整流程示例

### 首次使用流程

```bash
# 1. 快速配置（自动）
python setup_tencent.py
# 选择 "1. 首次下载（快速）"

# 2. 下载数据
python init_first_run.py
# 等待30-40分钟

# 3. 测试配置
python test_batch_setup.py

# 4. 运行分析
python src/volume_analyzer.py --no-update

# 5. 添加到 crontab
crontab -e
# 添加：30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
```

### 日常使用流程

```bash
# 已配置好 crontab，每天自动运行

# 手动运行（如需要）
python src/volume_analyzer.py

# 查看结果
ls -lh data/results/
```

## 监控和优化

### 监控下载进度

```bash
# Terminal 1: 查看日志
tail -f logs/*.log

# Terminal 2: 统计文件
watch -n 5 'echo "已下载: $(ls data/stocks/*.csv 2>/dev/null | wc -l) 个文件" && du -sh data/stocks'
```

### 性能调优

如果下载较慢：
```ini
# 增加线程数
max_workers = 15

# 缩短重试延迟
retry_delay = 3
```

如果失败较多：
```ini
# 降低线程数
max_workers = 5

# 增加重试次数
retry_times = 5
retry_delay = 10
```

## 从其他数据源切换

### 从 BaoStock 切换

```bash
# 1. 修改配置
python setup_tencent.py
# 选择 "2. 日常使用"

# 2. 重新下载（可选）
rm data/stocks/*.csv  # 清空旧数据
python init_first_run.py

# 3. 或者直接使用旧数据
python src/volume_analyzer.py
```

### 混合使用

```ini
# 首次下载用 Tencent（快）
source = tencent
max_workers = 10

# 下载完后切换到 BaoStock（完整）
# source = baostock
# max_workers = 1
```

## 进阶技巧

### 1. 分批下载

```python
# 分批下载大量股票
from src.data_downloader import DataDownloader

downloader = DataDownloader()
stock_list = downloader.download_stock_list()

# 每次1000只
for i in range(0, len(stock_list), 1000):
    batch = stock_list[i:i+1000]
    downloader.download_all_stocks(batch)
```

### 2. 自定义时间范围

修改 `config.ini`：
```ini
[Analysis]
min_history_days = 30   # 只下载30天（快）
min_history_days = 365  # 下载一年（完整）
```

### 3. 并行下载和分析

```bash
# Terminal 1: 持续更新数据
while true; do
    python -c "from src.data_downloader import DataDownloader; DataDownloader().download_all_stocks()"
    sleep 3600  # 每小时更新
done

# Terminal 2: 定时分析
watch -n 1800 'python src/volume_analyzer.py --no-update'
```

## 总结

使用 Tencent 数据源，你可以：

✅ **30-40分钟**完成首次下载（vs BaoStock的4-5小时）  
✅ **安全并发**下载，不用担心被限流  
✅ **简单配置**，一键启用多线程  
✅ **稳定可靠**，内置限流保护  

立即开始：

```bash
python setup_tencent.py
python init_first_run.py
python src/volume_analyzer.py --no-update
```

更多详细信息，请查看：
- `TENCENT_DATASOURCE_OPTIMIZATION.md` - 详细优化指南
- `VOLUME_ANALYZER_QUICKSTART.md` - 完整使用指南
