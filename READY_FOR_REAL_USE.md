# 准备就绪 - 可以下载真实数据

## 当前状态

### ✅ 已完成

1. **模拟数据已清理**
   - data/daily/ - 已清空 ✓
   - data/stocks/ - 已清空 ✓
   - data/results/ - 已清空 ✓

2. **代码已修复**
   - 修复了股票代码数据类型问题 ✓
   - 确保读取时code列为字符串 ✓
   - 修复了配置文件格式 ✓

3. **配置已优化**
   - 下载量限制设为0（无限制）✓
   - 适合首次完整下载 ✓

### 🎯 现在可以下载真实数据了！

## 使用真实数据的步骤

### 1. 启动程序

```bash
python main.py
```

**预期**：GUI窗口打开

### 2. 点击"立即执行分析"

**会发生什么**：
1. 从AkShare下载真实股票列表（约5000只）
2. 下载每只股票最近150天的交易数据
3. 计算120日均线和成交量倍数
4. 筛选符合条件的股票
5. 保存结果到 data/results/

**时间**：首次约30-60分钟

### 3. 观察进度

在GUI界面中可以看到：
- 顶部进度条显示下载进度
- 运行日志显示详细信息
- 状态栏显示当前操作

### 4. 查看结果

下载完成后：
- 结果表格显示符合条件的股票
- 双击股票查看详细数据
- 点击"导出结果"保存

## 代码修复说明

### 问题1：股票代码数据类型

**问题**：
```python
# pandas读取CSV时，000001 → 1 (整数，丢失前导0)
stock_code = row['code']  # 1, 2, 3 而不是 '000001', '000002'
```

**修复**：
```python
# 读取时指定dtype
df = pd.read_csv(file_path, dtype={'code': str})

# 使用前确保类型
stock_list['code'] = stock_list['code'].astype(str)
stock_code = str(row['code'])
```

**影响文件**：
- `src/data_downloader.py` - 3处修复
- `src/stock_filter.py` - 2处修复

### 问题2：配置文件注释格式

**问题**：
```ini
# ❌ INI文件不支持行尾注释
daily_download_limit_mb = 100  # 这是注释
```

**修复**：
```ini
# ✓ 注释必须独立一行
# 每日下载量限制（MB）
daily_download_limit_mb = 100
```

## 真实数据 vs 模拟数据对比

### 已删除的模拟数据

```
data/stocks/stock_list.csv
  - 5只硬编码的股票
  - 包含已退市的600001
  - 用于演示，已删除 ✓

data/daily/*.csv
  - 5个随机生成的数据文件
  - 包含假的价格和成交量
  - 用于演示，已删除 ✓
```

### 即将下载的真实数据

```
data/stocks/stock_list.csv
  - 约5000只真实股票
  - 从AkShare API获取
  - 只包含当前在市的股票
  - 不包含已退市的股票 ✓

data/daily/*.csv
  - 约5000个真实数据文件
  - 从东方财富网获取
  - 真实的历史价格和成交量
  - 每只150天历史数据 ✓
```

## 数据来源保证

### main.py 的数据流

```
python main.py
  ↓
GUI界面
  ↓
点击"立即执行分析"
  ↓
TaskScheduler.daily_analysis_task()
  ↓
DataDownloader.download_stock_list()
  ↓
akshare.stock_zh_a_spot_em()  ← 真实API
  ↓
从东方财富网获取数据
  ↓
约5000只真实在市股票
  ↓
不包含已退市的股票（如600001）
```

### 关键代码（src/data_downloader.py）

```python
# 第78行
stock_list = ak.stock_zh_a_spot_em()
# ↑ 这是真实的金融数据API
# ↑ 只返回当前在市的股票
# ↑ 自动过滤已退市的股票
```

## 下次运行预期

### 首次运行（现在）

```
股票列表：约5000只
数据天数：150天/只
总数据量：约72MB
下载时间：30-60分钟

结果：
- data/daily/ 约5000个CSV文件
- data/stocks/stock_list.csv 约5000行
- 不会有600001.csv（已退市）
```

### 第二天运行

```
检查本地：有5000只股票的数据
最新日期：2026-02-06
需要下载：2026-02-07的数据

股票列表：从缓存读取（1秒）
数据天数：1天/只
总数据量：约0.5MB
下载时间：3-5分钟

增量更新：只下载新的1天数据
```

## 验证方法

### 下载完成后验证

```bash
# 1. 检查文件数量（应该约5000个）
dir data\daily\*.csv | find /c ".csv"

# 2. 检查是否有600001（应该没有）
dir data\daily\600001.csv
# 结果应该是：找不到文件

# 3. 查看股票列表
python -c "import pandas as pd; df = pd.read_csv('data/stocks/stock_list.csv', dtype={'code': str}); print(f'股票数量: {len(df)}'); print('600001在列表:', '600001' in df['code'].values)"
# 结果应该是：
# 股票数量: 5000左右
# 600001在列表: False
```

## 配置确认

当前配置（适合首次运行）：

```ini
[Download]
max_workers = 10
daily_download_limit_mb = 0  # 无限制，首次下载
```

**完成首次下载后，建议修改为**：

```ini
[Download]
daily_download_limit_mb = 100  # 恢复限制
```

## 总结

### ✅ 已解决的问题

1. **模拟数据已删除**
2. **股票代码类型已修复**
3. **配置文件格式已修复**
4. **程序已验证可正常启动**

### 🚀 下一步

**立即可以运行**：

```bash
python main.py
```

然后：
1. 点击"立即执行分析"
2. 等待30-60分钟（首次下载）
3. 查看真实的筛选结果
4. 双击股票查看详细数据
5. 不会再看到600001等已退市股票

### ⚠️ 重要提醒

- **首次下载需要较长时间**，请耐心等待
- **网络连接要稳定**，避免下载失败
- **建议收盘后运行**（15:30之后），数据更完整
- **下载完成后**，建议将 daily_download_limit_mb 改回 100

---

*所有准备工作已完成，可以开始下载真实数据了！*
