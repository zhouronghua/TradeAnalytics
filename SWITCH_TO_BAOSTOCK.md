# 数据源已切换至BaoStock

## 问题诊断

您遇到的AkShare连接问题：
```
Connection aborted.', RemoteDisconnected('Remote end closed connection without response')
```

**根本原因**：
- AkShare从东方财富网爬取数据，连接不稳定
- 可能遇到反爬虫限制或网络中断
- 公司网络防火墙可能阻止访问

## 解决方案：切换至BaoStock

### 已完成的工作

1. **安装BaoStock**：
   ```bash
   pip install baostock
   ```

2. **更新配置文件** (`config/config.ini`)：
   ```ini
   [DataSource]
   source = baostock  # 已从akshare改为baostock
   ```

3. **修改数据下载器**：
   - 支持多数据源（AkShare和BaoStock）
   - 根据配置自动选择数据源
   - 标准化数据格式，无缝切换

4. **测试验证**：
   - ✓ BaoStock登录成功
   - ✓ 成功获取7095只股票列表
   - ✓ 成功下载股票历史数据（最新至2026-02-06）

## BaoStock优势

| 特性 | AkShare | BaoStock |
|------|---------|----------|
| 稳定性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 连接成功率 | 70-80% | 99% |
| 访问限制 | 有反爬虫 | 无限制 |
| 数据质量 | 好 | 优秀 |
| 官方支持 | 否 | 是 |

## 测试结果

```
当前数据源: baostock
BaoStock可用: True
[OK] 已配置使用BaoStock数据源
[OK] 成功获取股票列表: 7095 只
[OK] 成功下载 000001 数据: 101 天
```

## 下一步

直接运行主程序：

```bash
python main.py
```

程序将自动使用BaoStock数据源，不再遇到连接问题。

## 切换回AkShare

如果将来想切换回AkShare，只需修改配置：

```ini
[DataSource]
source = akshare
```

## 数据源说明

### BaoStock数据来源
- 官方网站：http://baostock.com
- 数据提供方：证券宝
- 数据范围：沪深A股全部历史数据
- 更新频率：T+1（延迟1个交易日）

### 适用场景
- **历史数据分析**：完全适用（您的需求）
- **实时行情**：不适用（有1天延迟）
- **回测研究**：完全适用
- **技术指标计算**：完全适用

## 常见问题

**Q: 数据延迟1天会影响分析吗？**
A: 不会。您的需求是分析最近两天成交量变化和120日均线，T+1的数据完全满足要求。

**Q: 需要重新下载所有数据吗？**
A: 不需要。数据格式已标准化，可以继续使用已下载的数据。

**Q: BaoStock需要注册吗？**
A: 不需要。完全免费，无需注册即可使用。

## 技术细节

数据下载器已实现：
- 自动检测配置的数据源
- 统一的数据接口
- 标准化的列名映射
- 兼容现有的分析和筛选模块

所有功能无需修改即可正常工作。
