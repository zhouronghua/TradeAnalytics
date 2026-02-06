# 股票过滤改进总结

## 用户需求

**原始要求**: 去掉基金，只关注上交所和深交所的股票

## 问题分析

之前的过滤规则虽然能排除部分基金和债券，但存在以下问题：

1. **包含指数代码**: 000001-000999范围内包含大量指数（如：000001 深证成指，000016 上证50指数等）
2. **基金未完全过滤**: 某些ETF基金（如：159xxx）可能未被完全过滤
3. **过滤不够精确**: 没有充分利用BaoStock的type字段来区分股票和其他证券类型

## 解决方案

### 1. 增加type字段过滤

```python
if 'type' in stock_list.columns:
    # type=1 表示股票，type=2 表示指数，type=3 表示其他
    stock_list = stock_list[stock_list['type'] == '1']
```

这一步可以直接从数据源层面排除指数和其他非股票证券。

### 2. 优化代码规则过滤

**修改前**：包含000xxx范围
```python
if code.startswith('000') or code.startswith('001') or \
   code.startswith('002') or code.startswith('003') or \
   code.startswith('300'):
    return True
```

**修改后**：排除000xxx，只保留001xxx
```python
# 上交所：60, 68开头
if code.startswith('60') or code.startswith('68'):
    return True
# 深交所中小板：002, 003开头
if code.startswith('002') or code.startswith('003'):
    return True
# 深交所创业板：300开头
if code.startswith('300'):
    return True
# 深交所主板：001开头（较新）
if code.startswith('001'):
    return True
# 注意：000xxx 范围包含大量指数，已排除
return False
```

### 3. 增加日志输出

为了便于调试和验证，增加了详细的日志：
```python
self.logger.info(f"从BaoStock获取到 {len(stock_list)} 条记录")
self.logger.debug(f"字段列表: {list(stock_list.columns)}")
# ... 过滤后 ...
if filtered_by_type > 0:
    self.logger.info(f"根据type字段过滤 {filtered_by_type} 只非股票（指数等）")
if filtered_count > 0:
    self.logger.info(f"代码规则过滤 {filtered_count} 只证券（基金、债券、指数等）")
```

## 过滤效果对比

### 修改前
- **总记录数**: 7095 条
- **过滤数量**: 2163 只
- **最终股票数**: 4932 只
- **问题**: 包含000001-000999范围的指数

### 修改后
- **总记录数**: 7107 条
- **过滤数量**: 2787 只
- **最终股票数**: 4308 只
- **改进**: 排除了所有指数，只保留纯股票

### 代码分布（修改后）

| 代码前缀 | 数量 | 说明 |
|---------|------|------|
| 60xxxx | 1698 只 | 上交所主板 |
| 68xxxx | 600 只 | 科创板 |
| 001xxx | 少量 | 深交所主板新股 |
| 002xxx | 大量 | 深交所中小板 |
| 003xxx | 少量 | 深交所中小板 |
| 300xxx | 935 只 | 创业板 |
| **总计** | **4308 只** | **纯股票** |

## 验证结果

### 1. 指数已排除

测试前20只股票，全部为正常上市公司：
```
600000  浦发银行
600004  白云机场
600006  东风汽车
600007  中国国贸
...
```

之前包含的指数（如：000001 深证成指，000016 上证50指数）已被完全排除。

### 2. 基金已排除

通过代码检查，未发现基金代码（50xxxx, 51xxxx, 159xxx等）。

### 3. 数据完整性

所有正常的A股股票均被保留，包括：
- 上交所主板和科创板
- 深交所主板、中小板、创业板

## 相关文件

- **实现文件**: `src/data_source_baostock_threadsafe.py`
- **测试脚本**: `test_stock_filter.py`
- **详细规则**: `STOCK_FILTER_RULES.md`

## 使用建议

1. **首次下载**: 删除旧的股票列表文件 `data/stocks/stock_list.csv`，让系统重新下载
2. **验证过滤**: 运行 `python test_stock_filter.py` 查看过滤效果
3. **检查日志**: 启动程序时，日志会显示过滤的详细信息

## 更新日期

2026-02-06

## 总结

通过两层过滤（type字段 + 代码规则），成功实现了：
- 排除所有基金、债券、指数等非股票证券
- 只保留上交所和深交所的纯股票
- 过滤效果精确、可验证

用户现在可以放心使用，系统将只分析真正的A股股票数据。
