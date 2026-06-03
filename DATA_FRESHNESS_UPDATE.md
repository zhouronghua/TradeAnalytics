# 数据时效性改进说明

## 更新时间
2026-06-03

## 问题描述

之前的版本存在一个问题：

如果股票数据长时间未更新，成交量分析可能会把**几个月前的旧数据**当作最新结果推送，导致用户收到过期的股票信息。

例如：
- 2026-01-15 发现某股票符合条件
- 数据一直未更新
- 2026-06-03 运行分析，仍然推送这个1月份的旧数据

## 解决方案

### 1. 添加数据时效性过滤

现在只会推送**最近2天**的数据：
- 当天的数据
- 前一天的数据

超过2天的数据会被自动过滤掉，不会出现在推送结果中。

### 2. 发送空通知

如果最近2天没有符合条件的股票：
- ✅ 发送空通知邮件
- ✅ 发送空通知方糖推送
- ✅ 明确说明"今日未发现符合条件的股票"

这样用户可以知道系统正常运行，只是暂时没有符合条件的股票。

## 技术实现

### 修改的函数

#### 1. `analyze_volume_surge()` 函数

新增 `max_days_old` 参数（默认2天）：

```python
def analyze_volume_surge(csv_files: List[str], 
                         max_days_old: int = 2) -> pd.DataFrame:
    """
    分析成交量暴涨股票
    
    Args:
        max_days_old: 最多保留几天前的数据（默认2天）
    """
    # ... 分析逻辑 ...
    
    # 过滤掉数据日期过旧的股票
    today = pd.Timestamp.now().normalize()
    cutoff_date = today - pd.Timedelta(days=max_days_old)
    results_df = results_df[results_df['date'] >= cutoff_date]
    
    return results_df
```

#### 2. `NotificationService.send_empty_analysis_result()` 方法

新增空结果推送方法：

```python
def send_empty_analysis_result(self, analysis_date: str,
                               strategy_meta: Dict) -> bool:
    """
    发送空分析结果通知
    """
    title = f"选股 {analysis_date} | 无符合标的"
    content = "今日未发现符合条件的股票。\n注意: 仅统计最近2天的数据。"
    return self._send_serverchan(title, content)
```

#### 3. `VolumeAnalyzer.run_batch_analysis()` 方法

更新日志和推送逻辑：

```python
# 执行分析（只保留最近2天的数据）
results_df = analyze_volume_surge(
    csv_files,
    max_days_old=2,  # 只保留最近2天的数据
)

if results_df.empty:
    self.logger.info("未找到符合条件的股票（仅统计最近2天的数据）")
    self.logger.info("注意：如果数据未更新，不会推送历史数据")
else:
    # 显示数据日期范围
    self.logger.info(f"数据日期范围: {min_date} 至 {max_date}")
```

## 使用示例

### 示例1: 有最近数据

```
[2026-06-03 15:30:01] [INFO] 找到 15 只符合条件的股票（最近2天）
[2026-06-03 15:30:01] [INFO] 数据日期范围: 2026-06-02 至 2026-06-03
[2026-06-03 15:30:02] [INFO] 邮件发送成功
[2026-06-03 15:30:03] [INFO] 方糖推送成功
```

推送内容：
```
选股 2026-06-03 MA20 量比>=5.0 | 15只

今日摘要
- 分析日期: 2026-06-03
- 符合条件股票: 15 只
- 数据日期: 最近2天

股票列表
1. 600000 浦发银行 ...
...
```

### 示例2: 无最近数据

```
[2026-06-03 15:30:01] [INFO] 未找到符合条件的股票（仅统计最近2天的数据）
[2026-06-03 15:30:01] [INFO] 注意：如果数据未更新，不会推送历史数据
[2026-06-03 15:30:02] [INFO] 已发送空结果邮件
[2026-06-03 15:30:03] [INFO] 已发送空结果方糖推送
```

推送内容：
```
选股 2026-06-03 MA20 量比>=5.0 | 无符合标的

今日摘要
- 分析日期: 2026-06-03
- 符合条件股票: 0 只

分析结果
今日未发现符合条件的股票。

注意: 仅统计最近2天的数据，不会推送历史数据。
```

## 配置选项

如果需要调整时效性窗口，可以修改代码：

```python
# 在 volume_analyzer.py 中
results_df = analyze_volume_surge(
    csv_files,
    max_days_old=1,  # 改为只保留当天数据
)

# 或者
results_df = analyze_volume_surge(
    csv_files,
    max_days_old=3,  # 改为保留3天数据
)
```

建议：
- **当天数据** (`max_days_old=1`): 最严格，适合实时监控
- **2天数据** (`max_days_old=2`): **推荐**，考虑T+1数据延迟
- **3天数据** (`max_days_old=3`): 较宽松，适合周末运行

## 与 T+1 数据的兼容性

由于 BaoStock 等数据源是 T+1（当天数据次日获取），建议：

### 运行时间建议

1. **下午3:30后运行**（当天收盘后）
   ```bash
   # crontab
   30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
   ```
   - 此时会有昨天的完整数据
   - 设置 `max_days_old=2` 可以捕获昨天和前天的数据

2. **次日早上运行**（获取昨日数据）
   ```bash
   # crontab
   0 9 * * 2-6 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
   ```
   - 此时昨天的数据已完整下载
   - 设置 `max_days_old=2` 可以捕获昨天和前天的数据

## 对比：修改前后

### 修改前

| 日期 | 数据 | 推送结果 |
|------|------|----------|
| 2026-01-15 | 股票A符合条件 | ✅ 推送 |
| 2026-06-03 | 数据未更新 | ❌ 推送1月的旧数据 |

### 修改后

| 日期 | 数据 | 推送结果 |
|------|------|----------|
| 2026-01-15 | 股票A符合条件 | ✅ 推送（当时） |
| 2026-06-03 | 数据未更新 | ✅ 推送空通知 |

## 日志说明

### 正常情况

```
[INFO] 找到 15 只符合条件的股票（最近2天）
[INFO] 数据日期范围: 2026-06-02 至 2026-06-03
```

### 数据过旧

```
[INFO] 未找到符合条件的股票（仅统计最近2天的数据）
[INFO] 注意：如果数据未更新，不会推送历史数据
```

### 数据未更新

如果看到这个日志，说明数据需要更新：
```
[WARNING] 数据更新部分失败: 总计5000, 成功4800, 失败200
[INFO] 未找到符合条件的股票（仅统计最近2天的数据）
```

解决方法：
```bash
# 手动更新数据
python -c "from src.data_downloader import DataDownloader; DataDownloader().download_all_stocks()"

# 或重新运行完整流程
python src/volume_analyzer.py
```

## 测试验证

### 测试1: 验证时效性过滤

```python
# 创建测试数据
import pandas as pd
from datetime import datetime, timedelta

# 创建包含不同日期的测试数据
test_data = [
    {'stock_code': '600000', 'date': datetime.now().strftime('%Y-%m-%d')},           # 今天
    {'stock_code': '600001', 'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')},  # 昨天
    {'stock_code': '600002', 'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')},  # 3天前
    {'stock_code': '600003', 'date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}, # 30天前
]

# 运行分析
results = analyze_volume_surge(csv_files, max_days_old=2)

# 预期结果：只有600000和600001
# 600002和600003会被过滤掉
```

### 测试2: 验证空通知

```bash
# 清空数据目录（模拟数据过旧）
rm data/stocks/*.csv

# 运行分析
python src/volume_analyzer.py --no-update

# 预期结果：
# - 日志显示"未找到符合条件的股票"
# - 发送空结果邮件
# - 发送空结果方糖推送
```

## 常见问题

### Q1: 为什么设置为2天而不是1天？

A: 考虑到：
1. **T+1数据延迟**：当天数据要次日才能获取
2. **周末和节假日**：可能跨越多天
3. **数据更新延迟**：给数据源一些缓冲时间

### Q2: 如果周五运行，会统计哪些数据？

A: 假设今天是周五（2026-06-06）：
- 包含：周五（06-06）和周四（06-05）的数据
- 排除：周三（06-04）及之前的数据

### Q3: 如果数据更新失败，会怎样？

A: 
1. 继续使用现有数据分析
2. 但只统计最近2天的数据
3. 如果现有数据都超过2天，发送空通知
4. 日志会提示数据更新失败

### Q4: 可以关闭空通知吗？

A: 可以通过命令行参数：
```bash
# 不发送邮件和推送
python src/volume_analyzer.py --no-email --no-notification

# 或者在配置文件中禁用
[Email]
enabled = false

[Notification]
enabled = false
```

### Q5: 如何验证数据是最新的？

A: 查看日志：
```
[INFO] 数据日期范围: 2026-06-02 至 2026-06-03
```

或检查数据文件：
```bash
# 查看最新修改的文件
ls -lt data/stocks/*.csv | head -5

# 查看某个文件的最新数据日期
tail -1 data/stocks/600000.csv
```

## 总结

这次改进确保了：

✅ **数据时效性**：只推送最近2天的数据  
✅ **避免误导**：不会推送几个月前的旧数据  
✅ **明确反馈**：无数据时发送空通知，而不是静默  
✅ **T+1兼容**：考虑数据延迟，使用2天窗口  
✅ **日志清晰**：明确说明数据日期范围  

用户现在可以放心地添加到 crontab 定时任务，不用担心收到过期的股票信息！
