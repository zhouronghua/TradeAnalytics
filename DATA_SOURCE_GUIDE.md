# 数据源切换指南

## AkShare数据源问题诊断

您遇到的错误信息：
```
Connection aborted.', RemoteDisconnected('Remote end closed connection without response')
```

### 问题原因

1. **AkShare数据源不稳定**：
   - AkShare从东方财富网爬取数据
   - 可能遇到反爬虫限制
   - 网络连接可能被中断
   - 高峰期访问限制

2. **网络环境**：
   - 公司网络可能有防火墙限制
   - 需要代理服务器
   - 访问频率过高

## 解决方案

### 方案1：使用BaoStock（推荐）

**BaoStock优势**：
- 更稳定可靠的数据源
- 官方API，不会被限制
- 数据质量高
- 完全免费

**切换方法**：

1. 已自动安装BaoStock：
   ```bash
   pip install baostock
   ```

2. 编辑配置文件 `config/config.ini`：
   ```ini
   [DataSource]
   # 数据源选择: akshare 或 baostock
   source = baostock
   ```

3. 重新运行程序：
   ```bash
   python main.py
   ```

### 方案2：优化AkShare设置

如果仍要使用AkShare，调整配置：

```ini
[Download]
max_workers = 3        # 降低并发数
retry_times = 5        # 增加重试次数
retry_delay = 10       # 增加重试间隔（秒）
```

### 方案3：错峰下载

避开交易时段，建议时间：
- 晚上19:00-23:00
- 周末
- 非交易日

### 方案4：使用代理

如果公司网络限制，设置代理：

**Windows**：
```cmd
set http_proxy=http://proxy.example.com:8080
set https_proxy=http://proxy.example.com:8080
```

**Linux/Mac**：
```bash
export http_proxy=http://proxy.example.com:8080
export https_proxy=http://proxy.example.com:8080
```

## 数据源对比

| 特性 | AkShare | BaoStock |
|------|---------|----------|
| 稳定性 | 一般 | 优秀 |
| 数据实时性 | 高 | 延迟1-2天 |
| 访问限制 | 有 | 无 |
| 数据质量 | 好 | 优秀 |
| 安装难度 | 简单 | 简单 |
| 推荐度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 配置说明

当前配置文件已更新为使用BaoStock：

```ini
[DataSource]
# 数据源选择: akshare 或 baostock
# akshare: 东方财富数据，实时性好但可能不稳定
# baostock: 证券宝数据，更稳定可靠，推荐使用
source = baostock
```

## 常见问题

### Q: BaoStock数据是否足够新？
A: BaoStock的数据通常延迟1-2天，对于历史数据分析完全够用。

### Q: 可以同时使用两个数据源吗？
A: 当前版本支持切换但不能同时使用。如果一个失败，可以手动切换到另一个。

### Q: 切换数据源后需要重新下载所有数据吗？
A: 不需要。两个数据源的数据格式已经标准化，可以无缝切换。

### Q: 如何知道当前使用的是哪个数据源？
A: 查看日志文件，会显示：
```
[INFO] [DataDownloader] 使用BaoStock数据源
```

## 下一步

建议您：
1. 使用BaoStock数据源（配置已更新）
2. 运行 `python main.py`
3. 如果还有问题，查看日志文件 `logs/xxx.log`
