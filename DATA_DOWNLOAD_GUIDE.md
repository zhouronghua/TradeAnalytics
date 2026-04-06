# A股历史数据下载与回测指南

## 一、数据源配置

**默认使用AkShare，无需注册Token**

### AkShare（默认，推荐）

- **优点**: 开源免费，无需注册，数据实时性好
- **缺点**: 部分接口偶尔不稳定，可通过重试机制解决

```bash
pip install akshare
```

### 其他可选数据源

#### BaoStock

- **优点**: 数据覆盖时间长，接口稳定
- **缺点**: 部分数据字段有限制

```bash
pip install baostock
# 修改 config/config.ini: source = baostock
```

#### Tushare Pro

- **优点**: 数据质量高，专业数据丰富
- **缺点**: 需要注册获取Token
- **注册**: https://tushare.pro/register

```bash
pip install tushare
export TUSHARE_TOKEN="your_token"
# 修改 config/config.ini: source = tushare
```

## 二、增量下载历史数据

### 首次下载（2020年至今）

```bash
# 使用AkShare（默认，无需Token）
python download_history_incremental.py --start-year 2020

# 或使用BaoStock
python download_history_incremental.py --source baostock --start-year 2020
```

### 后续增量更新（只下载新数据）

```bash
# 每天收盘后运行一次，自动增量更新
python download_history_incremental.py

# 指定并发数（根据网络调整）
python download_history_incremental.py --workers 10
```

### 查看下载进度

运行后会显示实时进度:
```
进度: 500/5300 (9.4%) 成功:480 失败:20 新下载:120 更新:360 已最新:20
```

## 三、妖股策略回测

### 基础回测（2020年至今）

```bash
python backtest_monster_stock_2020.py --start 2020-01-01
```

### 指定回测区间

```bash
# 2022年回测
python backtest_monster_stock_2020.py --start 2022-01-01 --end 2022-12-31

# 最近一年
python backtest_monster_stock_2020.py --start 2024-01-01
```

### 调整策略参数

```bash
# 降低评分阈值（更宽松的筛选）
python backtest_monster_stock_2020.py --min-score 70 --lookback 45

# 指定股票池测试
python backtest_monster_stock_2020.py --stocks 000001 000002 600000
```

### 保存详细结果

```bash
python backtest_monster_stock_2020.py --output results_2020_2024.csv
```

## 四、完整工作流程

### 首次部署

```bash
# 1. 安装依赖
pip install -r requirements.txt
# 默认使用AkShare，无需额外安装

# 2. 下载历史数据（首次约需1-2小时，取决于网络）
python download_history_incremental.py --start-year 2020 --workers 3

# 3. 运行回测
python backtest_monster_stock_2020.py --start 2020-01-01 --output backtest_2020_2024.csv
```

### 每日更新

```bash
# 收盘后增量更新（约5-10分钟）
python download_history_incremental.py

# 查看最新回测结果
python backtest_monster_stock_2020.py --start $(date -d '1 year ago' +%Y-%m-%d)
```

## 五、回测结果解读

回测报告包含：

```
回测区间: 2020-01-01 至 2024-12-31
信号总数: 1523
成功买入: 1489

【持有5日收益统计】
  有效样本: 1489
  平均收益: 3.45%
  中位数收益: 2.12%
  胜率: 58.3%
  最大收益: 45.67%
  最大亏损: -12.34%
  盈亏比: 2.15

【最近10个信号】
2024-12-20  600XXX  妖股名称  评分:85.2  买入价:15.32  5日收益:8.2%
...
```

**关键指标**:
- **胜率**: 盈利交易占比，越高越好
- **盈亏比**: 平均盈利/平均亏损，大于1才有正期望
- **中位数收益**: 比平均收益更能反映典型表现
- **最大亏损**: 评估单笔最大风险

## 六、常见问题

### Q: AkShare下载失败/数据为空怎么办？

**最常见原因：东方财富限流**

AkShare调用东方财富接口，如果频率过快会被服务器断开连接。

**解决方法**（按优先级）：

1. **单线程下载（默认已启用）**
   ```bash
   python download_history_incremental.py --workers 1
   ```
   首次下载约需2-3小时，这是避免限流的最佳方式。

2. **分批下载（如果中断）**
   ```bash
   # 下载会自动跳过已有数据的股票，可以重复运行
   python download_history_incremental.py
   # 如有失败，多运行几次直到全部成功
   ```

3. **增加重试次数**
   在 `config/config.ini` 中设置：
   ```ini
   retry_times = 5
   retry_delay = 5
   ```

4. **切换BaoStock数据源**
   ```bash
   python download_history_incremental.py --source baostock
   ```
   BaoStock接口更稳定，但部分数据字段可能不同。

5. **检查网络连接**
   ```bash
   curl -I https://push2.eastmoney.com/api/
   ```

### Q: 数据不完整？

检查本地数据日期范围：
```python
import pandas as pd
df = pd.read_csv('data/daily/000001.csv')
print(f"最早: {df['date'].min()}, 最新: {df['date'].max()}")
print(f"总行数: {len(df)}")
```

### Q: 回测无信号？

可能原因：
1. 数据不足（需要至少lookback_days + 20天的历史）
2. 评分阈值过高，尝试 `--min-score 60`
3. 市场确实没有出现符合条件的妖股

### Q: 增量下载会覆盖历史数据吗？

不会。增量下载会：
1. 保留已有的历史数据
2. 补充缺失的早期数据
3. 只下载最新的增量数据
4. 自动合并去重

## 七、性能优化建议

1. **首次下载**: 建议使用 `--workers 1` 避免限流，完整下载约需1-2小时
2. **日常更新**: 使用 `--workers 5` 或更高，约5-10分钟完成
3. **回测加速**: 指定股票池 `--stocks` 或缩小时间范围
4. **存储优化**: 定期清理 `data/daily/*.csv` 可节省空间

## 八、文件说明

- `download_history_incremental.py` - 增量下载主脚本
- `backtest_monster_stock_2020.py` - 妖股策略回测脚本
- `src/data_source_tushare.py` - Tushare数据源适配器
- `src/data_downloader.py` - 统一数据下载器
- `data/daily/*.csv` - 日线数据存储（每只一个文件）
- `config/config.ini` - 数据源配置
