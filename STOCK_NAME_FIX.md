# 股票名称显示修复

## 问题描述

在GUI的成交量分析结果中，"股票代码"和"股票名称"列显示的都是数字（股票代码），而不是真实的股票名称。

**示例**：
- 显示为：600000 -> 600000
- 应该是：600000 -> 浦发银行

## 根本原因

在`src/volume_analyzer.py`的`analyze_stock_flexible`函数中（原第121行），直接使用股票代码作为股票名称：

```python
'stock_name': stock_code,  # 暂时使用代码作为名称
```

虽然`data/stocks/stock_list.csv`文件中包含了完整的股票名称信息，但成交量分析器没有查询这个文件，导致结果中的股票名称都是代码。

## 解决方案

在`src/volume_analyzer.py`中添加了两个新函数：

### 1. `load_stock_list()` - 加载股票列表（带缓存）

```python
def load_stock_list() -> Optional[pd.DataFrame]:
    """加载股票列表（带缓存）"""
    global _stock_list_cache
    
    if _stock_list_cache is not None:
        return _stock_list_cache
    
    stock_list_file = './data/stocks/stock_list.csv'
    if os.path.exists(stock_list_file):
        try:
            _stock_list_cache = pd.read_csv(stock_list_file, dtype={'code': str})
            return _stock_list_cache
        except Exception as e:
            print(f"加载股票列表失败: {e}")
            return None
    return None
```

**特点**：
- 使用全局缓存避免重复加载
- 优化性能，特别是分析大量股票时

### 2. `get_stock_name()` - 根据代码获取名称

```python
def get_stock_name(stock_code: str) -> str:
    """根据股票代码获取股票名称"""
    stock_list = load_stock_list()
    
    if stock_list is None:
        return stock_code
    
    # 确保stock_code是6位字符串
    stock_code = str(stock_code).zfill(6)
    
    # 查找股票名称
    match = stock_list[stock_list['code'] == stock_code]
    if not match.empty and 'name' in match.columns:
        name = match.iloc[0]['name']
        # 如果name不为空且不等于code，返回name
        if pd.notna(name) and str(name) != stock_code:
            return str(name)
    
    return stock_code
```

**特点**：
- 自动格式化股票代码为6位（如`1` -> `000001`）
- 如果查询失败或stock_list不存在，返回股票代码作为fallback
- 安全处理各种边界情况

### 3. 修改结果生成逻辑

将原来的：
```python
'stock_name': stock_code,  # 暂时使用代码作为名称
```

改为：
```python
stock_name = get_stock_name(stock_code)  # 从股票列表中获取真实名称
...
'stock_name': stock_name,
```

## 修改的文件

- `src/volume_analyzer.py` - 添加股票名称查询功能

## 测试结果

```
测试股票名称查询:
  600000 -> 浦发银行 [成功-返回名称]
  603616 -> 乐凯胶片 [成功-返回名称]
  300666 -> 江特电机 [成功-返回名称]
  002462 -> 嘉事堂 [成功-返回名称]

测试成功：能够正确查询到股票名称
```

## 优势

1. **性能优化**：使用全局缓存，避免重复加载stock_list.csv
2. **容错性好**：如果stock_list不存在或查询失败，fallback到使用代码
3. **代码简洁**：一个函数调用即可获取股票名称
4. **自动格式化**：自动处理股票代码格式（补齐6位）

## 依赖关系

修复生效需要：
1. `data/stocks/stock_list.csv`文件存在
2. 文件包含`code`和`name`两列
3. 数据格式正确

如果stock_list.csv不存在或数据有问题，程序会自动降级到显示股票代码，不会报错。

## 使用建议

1. 确保至少运行过一次数据下载，生成stock_list.csv
2. 定期更新stock_list.csv以获取新上市股票信息
3. 如果看到某些股票仍然显示代码，可能是该股票不在列表中（如已退市）

## 后续优化

考虑添加：
- 实时从API查询股票名称的备用方案
- 自动下载缺失的股票列表
- 股票名称的本地持久化缓存
