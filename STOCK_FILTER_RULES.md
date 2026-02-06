# 股票过滤规则说明

## 目的

只下载和分析上交所和深交所的股票，排除基金、债券、权证等其他证券类型。

## 过滤规则

### 上交所（沪市）股票
- **主板股票**: 60xxxx（如：600000 浦发银行，601318 中国平安）
- **科创板**: 688xxx（如：688001 华兴源创）

### 深交所（深市）股票
- **主板股票**: 001xxx（如：001979）
- **中小板**: 002xxx, 003xxx（如：002415 海康威视）
- **创业板**: 300xxx（如：300059 东方财富）

**注意**: 000xxx 范围的代码中包含大量指数（如：000001 深证成指，000016 上证50指数等），因此被排除。真正的000xxx主板股票数量较少，如确需要可单独添加。

### 排除的证券类型

#### 基金
- **上交所基金**: 50xxxx, 51xxxx（如：510050 50ETF，159xxx ETF）
- **深交所基金**: 159xxx（如：159001 易方达深100ETF）

#### 债券
- **上交所债券**: 通常以 1、2、5、7、9 开头的特定格式
- **深交所债券**: 不同的编码规则

#### 其他
- **B股**: 上交所 900xxx，深交所 200xxx
- **权证**: 已基本退出市场

## 实现位置

**文件**: `src/data_source_baostock_threadsafe.py`

**方法**: `get_stock_list()`

**核心代码**:
```python
# 1. 首先根据type字段过滤（如果存在）
if 'type' in stock_list.columns:
    # type=1 表示股票，type=2 表示指数，type=3 表示其他
    stock_list = stock_list[stock_list['type'] == '1']

# 2. 然后根据代码规则精确过滤
def is_valid_stock(code):
    if len(code) != 6:
        return False
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

stock_list = stock_list[stock_list['code'].apply(is_valid_stock)]
```

## 效果

- 自动过滤掉所有基金（如：510050, 159001等）
- 自动过滤掉所有债券
- 自动过滤掉B股和其他非A股证券
- 只保留正常交易的A股股票

## 验证

启动程序后，在日志中会看到：
```
[INFO] [BaoStock] 从BaoStock获取到 7107 条记录
[INFO] [BaoStock] 代码规则过滤 2787 只证券（基金、债券、指数等）
[INFO] [BaoStock] 获取到 4308 只股票
```

### 过滤效果统计（2026-02-06）
- **原始记录数**: 7107 条
- **过滤数量**: 2787 只（基金、债券、指数等）
- **最终股票数**: 4308 只

### 代码分布
- 00xxxx: 1075 只（深交所主板，排除指数后）
- 30xxxx: 935 只（创业板）
- 60xxxx: 1698 只（上交所主板）
- 68xxxx: 600 只（科创板）

## 更新日期

2026-02-06
