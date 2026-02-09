# 非交易日自动回退功能

## 问题描述

在非交易日（周末、节假日）运行程序时，BaoStock API的`query_all_stock(day=当天日期)`会返回空数据，导致无法获取股票列表。

## 解决方案

实现了**自动回退到最近交易日**的功能：

1. 首先尝试查询当天日期
2. 如果返回空数据，自动向前查询最多7天
3. 跳过周末（周六、周日）
4. 找到第一个有数据的交易日即停止
5. 如果7天内都没有数据，返回空DataFrame

## 实现细节

### 修改的文件

1. `src/data_source_baostock_threadsafe.py` - 线程安全版本（主要使用）
2. `src/data_source_baostock.py` - 普通版本（保持一致性）

### 核心逻辑

```python
# 检查是否为空，可能是非交易日
if len(stock_list) == 0:
    self.logger.warning(f"查询日期 {query_date} 返回空数据，可能是非交易日")
    
    # 尝试查询最近的交易日（向前查询最多7天）
    for days_back in range(1, 8):
        retry_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        # 跳过周末
        retry_datetime = datetime.now() - timedelta(days=days_back)
        if retry_datetime.weekday() >= 5:  # 周六或周日
            continue
        
        self.logger.info(f"尝试查询 {retry_date}...")
        rs_retry = bs.query_all_stock(day=retry_date)
        
        if rs_retry.error_code == '0':
            data_list_retry = []
            while rs_retry.next():
                data_list_retry.append(rs_retry.get_row_data())
            
            if len(data_list_retry) > 0:
                self.logger.info(f"成功从 {retry_date} 获取到 {len(data_list_retry)} 条记录")
                stock_list = pd.DataFrame(data_list_retry, columns=rs_retry.fields)
                break
```

## 测试结果

在周日（2026-02-09）测试：

```
[INFO] [BaoStock] 查询日期: 2026-02-09
[INFO] [BaoStock] 从BaoStock获取到 0 条记录
[WARNING] [BaoStock] 查询日期 2026-02-09 返回空数据，可能是非交易日
[INFO] [BaoStock] 尝试查询 2026-02-06...
[INFO] [BaoStock] 成功从 2026-02-06 获取到 7118 条记录
[INFO] [BaoStock] 获取到 4308 只股票
```

成功结果：
- 自动从周日回退到周四（2026-02-06）
- 获取到4308只A股股票
- 程序完全正常运行

## 优势

1. **用户友好**：周末也能正常使用程序
2. **自动化**：无需手动配置或切换数据源
3. **可靠性**：自动处理各种非交易日情况
4. **向后兼容**：不影响交易日的正常使用

## 适用场景

- 周末运行程序
- 节假日运行程序
- 首次安装时在非交易日运行
- 长假后首次运行（会获取最近一个交易日的数据）

## 注意事项

1. 获取的是最近交易日的股票列表，不是实时数据
2. 如果最近7天内都没有交易日（极少见），会返回空DataFrame
3. 历史行情数据下载不受此影响，会根据实际交易日下载

## 后续建议

考虑到数据的时效性，可以：
1. 在界面上显示获取的数据日期
2. 提供手动刷新功能
3. 在工作日自动更新到最新数据
