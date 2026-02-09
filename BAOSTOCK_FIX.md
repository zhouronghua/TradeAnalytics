# BaoStock股票列表获取修复

## 问题描述

在获取BaoStock股票列表时出现错误：

```
[2026-02-08 12:17:09] [INFO] [BaoStock] 获取到 0 只股票
[2026-02-08 12:17:09] [ERROR] [BaoStock] 获取股票列表异常: "None of [Index(['code', 'name'], dtype='str')] are in the [columns]"
[2026-02-08 12:17:09] [ERROR] [DataDownloader] 获取股票列表失败
[2026-02-08 12:17:09] [ERROR] [TaskScheduler] 获取股票列表失败
```

## 根本原因

代码在返回`stock_list[['code', 'name']]`时，没有检查这些列是否存在。当：
1. BaoStock API返回空数据
2. API返回的字段名称发生变化
3. 数据处理过程中列名丢失

会导致KeyError异常。

## 修复方案

### 1. 添加空数据检查

在处理之前检查DataFrame是否为空：

```python
if len(stock_list) == 0:
    self.logger.warning("BaoStock返回的股票列表为空")
    return pd.DataFrame(columns=['code', 'name'])
```

### 2. 改进日志输出

将字段列表的日志级别从DEBUG改为INFO，方便排查问题：

```python
self.logger.info(f"字段列表: {list(stock_list.columns)}")
```

### 3. 安全的列重命名

检查列是否存在后再重命名：

```python
rename_map = {}
if 'code_name' in stock_list.columns:
    rename_map['code_name'] = 'name'
if 'tradeStatus' in stock_list.columns:
    rename_map['tradeStatus'] = 'status'

if rename_map:
    stock_list.rename(columns=rename_map, inplace=True)
    self.logger.info(f"列重命名: {rename_map}")
else:
    self.logger.warning(f"未找到需要重命名的列，当前列: {list(stock_list.columns)}")
```

### 4. 返回前检查必需列

确保返回的DataFrame包含必需的列：

```python
if 'code' not in stock_list.columns:
    self.logger.error(f"结果中缺少'code'列，当前列: {list(stock_list.columns)}")
    return None

if 'name' not in stock_list.columns:
    self.logger.warning(f"结果中缺少'name'列，将使用股票代码作为名称")
    stock_list['name'] = stock_list['code']
```

### 5. 条件过滤

在过滤前检查字段是否存在：

```python
if 'status' in stock_list.columns:
    stock_list = stock_list[stock_list['status'] == '1']
else:
    self.logger.warning("没有找到'status'字段，无法按交易状态过滤")
```

## 修改的文件

1. `src/data_source_baostock_threadsafe.py` - 线程安全版本
2. `src/data_source_baostock.py` - 普通版本

## 测试结果

修复后，即使BaoStock返回空数据（可能是非交易日或API问题），程序也能正常处理，返回空的DataFrame而不是抛出异常。

```
[2026-02-08 12:18:49] [INFO] [BaoStock] 从BaoStock获取到 0 条记录
[2026-02-08 12:18:49] [INFO] [BaoStock] 字段列表: ['code', 'tradeStatus', 'code_name']
[2026-02-08 12:18:49] [WARNING] [BaoStock] BaoStock返回的股票列表为空
警告：返回空DataFrame
列: ['code', 'name']
测试通过
```

## 可能的后续问题

如果BaoStock API的字段名称发生变化，现在的代码会：
1. 记录详细的字段列表到日志
2. 尝试安全地重命名
3. 如果缺少必需字段，返回None并记录错误
4. 如果缺少可选字段（如name），使用stock code作为fallback

这样可以更容易地诊断和修复API变化导致的问题。

## 注意事项

今天（2026-02-08）是周六，不是交易日，BaoStock API可能返回空数据是正常的。建议在工作日测试以验证完整功能。
