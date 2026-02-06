# 新增功能说明

## 2026-02-06 更新

### 1. 下载量限制功能

**功能描述**：
为了保护网络资源和避免频繁请求被封IP，增加了每日下载量限制功能。

**配置文件** (`config/config.ini`):
```ini
[Download]
daily_download_limit_mb = 100  # 每日下载量限制（MB），0表示无限制
```

**实现细节**：
- 在 `DataDownloader` 类中添加下载量统计
- 每次保存数据时累计下载字节数
- 达到限制后自动停止下载
- 提供 `get_download_stats()` 方法查询统计信息

**使用方法**：
```python
downloader = DataDownloader()

# 检查是否可以继续下载
if downloader.check_download_limit():
    # 执行下载
    downloader.update_stock_data(stock_code)

# 查看下载统计
stats = downloader.get_download_stats()
print(f"已下载: {stats['downloaded_mb']:.2f}MB")
print(f"限制: {stats['limit_mb']:.0f}MB")
print(f"使用率: {stats['percentage']:.1f}%")
```

**日志输出示例**：
```
[2026-02-06 16:49:40] [INFO] [DataDownloader] 数据下载器初始化完成（每日下载限制: 100MB）
[2026-02-06 16:49:40] [INFO] [DataDownloader] 下载完成！成功: 850, 失败: 15
[2026-02-06 16:49:40] [INFO] [DataDownloader] 下载数据量: 98.50MB / 100MB (98.5%)
[2026-02-06 16:49:40] [WARNING] [DataDownloader] 已达到每日下载限制 (100.00MB / 100MB)
```

---

### 2. 股票详情查看功能

**功能描述**：
在筛选结果表格中，双击任意股票可以查看该股票的详细历史数据。

**使用方法**：
1. 在主界面的"筛选结果"标签页中
2. 双击表格中的任意股票行
3. 弹出详情窗口显示完整的股票数据

**详情窗口包含**：
- **基本信息区**：
  - 股票代码和名称
  - 数据天数和日期范围
  - 最新交易日数据（开盘、收盘、最高、最低、成交量、成交额）
  - 统计数据（最高价、最低价、均价、平均成交量）

- **历史数据表格**：
  - 显示最近100天的交易数据
  - 包含：日期、开盘、收盘、最高、最低、成交量、成交额
  - 支持滚动查看

- **操作按钮**：
  - 导出数据：将股票完整数据导出为CSV文件
  - 关闭：关闭详情窗口

**界面截图说明**：
```
┌─────────────────────────────────────────────────────────┐
│ 股票详情 - 600001 邯郸钢铁                               │
├─────────────────────────────────────────────────────────┤
│ ┌───────────────── 基本信息 ────────────────────┐       │
│ │ 股票代码: 600001                               │       │
│ │ 股票名称: 邯郸钢铁                             │       │
│ │ 数据天数: 150天                                │       │
│ │ 日期范围: 2025-09-09 ~ 2026-02-05             │       │
│ │                                                │       │
│ │ 最新数据 (2026-02-05):                        │       │
│ │   收盘价: 6.99                                 │       │
│ │   开盘价: 6.92                                 │       │
│ │   最高价: 7.13                                 │       │
│ │   最低价: 6.85                                 │       │
│ │   成交量: 17,058,776                          │       │
│ │   成交额: 119.23M                             │       │
│ └────────────────────────────────────────────────┘       │
│                                                           │
│ ┌───────────────── 历史数据 ────────────────────┐       │
│ │ 日期       开盘  收盘  最高  最低  成交量  成交额│       │
│ │ 2026-02-05 6.92  6.99  7.13  6.85  17M   119M │       │
│ │ 2026-02-04 6.85  6.87  6.92  6.80  2.6M  18M  │       │
│ │ ...                                            │       │
│ └────────────────────────────────────────────────┘       │
│                                                           │
│ [导出数据] [关闭]           显示最近100天数据，共150天   │
└─────────────────────────────────────────────────────────┘
```

**实现代码位置**：
- `src/gui.py` 中的 `on_stock_double_click()` 方法
- `src/gui.py` 中的 `show_stock_detail()` 方法

---

## 技术细节

### 下载量统计算法

每个CSV文件的大小估算：
```python
# 估算公式：每行约100字节
estimated_size = len(df) * 100

# 例如：
# - 150天数据 = 150 * 100 = 15KB
# - 5000只股票 * 15KB = 75MB（实际下载量）
```

### 增量下载机制

确保第二天只下载新数据：
```python
# 1. 检查本地数据最新日期
latest_date = pd.to_datetime(local_df['date']).max()
start_date = (latest_date + timedelta(days=1)).strftime('%Y%m%d')

# 2. 判断是否需要更新
if start_date >= datetime.now().strftime('%Y%m%d'):
    # 数据已是最新，跳过下载
    return True

# 3. 只下载增量数据
new_df = self.download_stock_history(stock_code, start_date=start_date)

# 4. 合并数据
combined_df = pd.concat([local_df, new_df])
```

---

## 配置参数说明

### 完整配置文件

```ini
[Paths]
data_dir = ./data
daily_dir = ./data/daily
stocks_dir = ./data/stocks
results_dir = ./data/results
logs_dir = ./logs

[DataSource]
source = akshare
update_stock_list_days = 1

[Analysis]
ma_period = 120
volume_ratio_threshold = 5.0
min_history_days = 150

[Scheduler]
enabled = true
run_time = 15:30
weekdays_only = true

[Download]
max_workers = 10
retry_times = 3
retry_delay = 5
# 每日下载量限制（MB），0表示无限制
daily_download_limit_mb = 100

[GUI]
window_width = 1200
window_height = 800
theme = default
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| daily_download_limit_mb | 100 | 每日下载量限制（MB），0表示无限制 |
| ma_period | 120 | 移动平均线周期（天） |
| volume_ratio_threshold | 5.0 | 成交量倍数阈值 |
| min_history_days | 150 | 历史数据天数 |
| max_workers | 10 | 下载并发数 |

---

## 使用建议

### 首次运行

1. **设置合理的下载限制**：
   - 首次运行建议设置为 0（无限制）或较大值（如200MB）
   - 完成首次下载后改为 100MB

2. **分批下载**：
   - 如果数据量很大，可以分多天下载
   - 每天下载一部分，逐步积累数据

### 日常使用

1. **保持默认设置**：
   - daily_download_limit_mb = 100
   - 每天只需下载当天新数据（约5MB）
   - 完全在限制范围内

2. **查看股票详情**：
   - 在结果表格中双击感兴趣的股票
   - 查看完整历史数据和统计信息
   - 导出数据进行进一步分析

---

## 已知限制

1. **下载量估算**：
   - 使用简单的估算公式（每行100字节）
   - 实际大小可能略有差异
   - 建议保留一些余量

2. **详情窗口**：
   - 默认只显示最近100天数据（性能考虑）
   - 导出功能可以获取完整数据

---

## 后续优化建议

1. **下载统计优化**：
   - 更精确的文件大小计算
   - 区分首次下载和增量下载的限制
   - 添加下载速度监控

2. **详情窗口增强**：
   - 添加K线图可视化
   - 显示更多技术指标
   - 支持日期范围筛选

3. **数据导出增强**：
   - 支持多种格式（Excel、JSON）
   - 批量导出多只股票
   - 自定义导出字段
