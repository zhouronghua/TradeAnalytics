# 线程安全问题修复说明

## 问题描述

启动程序后出现以下错误：
```
'ThreadSafeBaoStockDataSource' object has no attribute 'logged_in'
```

## 根本原因

在线程安全版本的BaoStock实现中，`logged_in`状态存储在线程本地存储（`threading.local()`）中，具体是`self.local.logged_in`，而不是类的实例属性`self.logged_in`。

但在`data_downloader.py`中，原来的代码试图直接访问`self.baostock_source.logged_in`，导致属性不存在错误。

## 修复方法

由于线程安全版本已经通过`_ensure_login()`方法自动处理了登录逻辑（在每个线程首次调用时自动登录），因此不再需要在`data_downloader.py`中手动检查和处理登录状态。

### 修改位置

**文件**: `src/data_downloader.py`

**修改1**: `download_stock_list`方法
```python
# 修改前（错误）：
if self.data_source == 'baostock' and self.baostock_source:
    # 使用BaoStock
    if not self.baostock_source.logged_in:  # 错误：线程安全版本无此属性
        if not self.baostock_source.login():
            self.logger.error("BaoStock登录失败")
            # 尝试读取本地缓存
            if os.path.exists(stock_list_file):
                self.logger.info("从本地缓存读取股票列表")
                return safe_read_csv(stock_list_file, dtype={'code': str})
            return None
    
    stock_list = self.baostock_source.get_stock_list()

# 修改后（正确）：
if self.data_source == 'baostock' and self.baostock_source:
    # 使用BaoStock（线程安全版本会自动处理登录）
    stock_list = self.baostock_source.get_stock_list()
```

**修改2**: `download_stock_history`方法
```python
# 修改前（错误）：
if self.data_source == 'baostock' and self.baostock_source:
    # 使用BaoStock
    if not self.baostock_source.logged_in:  # 错误：线程安全版本无此属性
        if not self.baostock_source.login():
            self.logger.error("BaoStock未登录")
            return None
    
    df = self.baostock_source.get_stock_history(
        stock_code=stock_code,
        start_date=start_date_fmt,
        end_date=end_date_fmt
    )

# 修改后（正确）：
if self.data_source == 'baostock' and self.baostock_source:
    # 使用BaoStock（线程安全版本会自动处理登录）
    df = self.baostock_source.get_stock_history(
        stock_code=stock_code,
        start_date=start_date_fmt,
        end_date=end_date_fmt
    )
```

## 工作原理

线程安全版本的BaoStock（`ThreadSafeBaoStockDataSource`）通过以下机制自动处理登录：

1. 每个线程有独立的线程本地存储（`self.local`）
2. `_ensure_login()`方法在每次获取数据前自动被调用
3. 如果当前线程还未登录（检查`self.local.logged_in`），则自动执行登录
4. 登录成功后设置`self.local.logged_in = True`

因此，调用方无需手动管理登录状态，只需直接调用`get_stock_list()`或`get_stock_history()`即可。

## 验证

修复后，程序可以正常启动，多线程下载也不会再出现`'logged_in'`属性错误。日志显示：
```
[INFO] [DataDownloader] 使用BaoStock数据源（线程安全版本）
```

## 日期

2026-02-06
