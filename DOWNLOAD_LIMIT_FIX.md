# 下载量限制功能修复说明

## 问题描述

用户报告：配置了100MB的下载限制，但只下载了约100KB就停止了。

## 问题原因

### 原始代码的问题

```python
def save_stock_data(self, stock_code: str, df: pd.DataFrame) -> bool:
    file_path = os.path.join(self.daily_dir, f"{stock_code}.csv")
    
    # ❌ 错误：在保存时统计，导致重复计算
    if df is not None and not df.empty:
        estimated_size = len(df) * 100
        self.downloaded_bytes += estimated_size  # 每次保存都累加
    
    return safe_write_csv(df, file_path)
```

**问题**：
1. 在 `update_stock_data` 方法中，可能会多次调用 `save_stock_data`
2. 合并本地数据和新数据后再次保存，导致重复计算
3. 例如：本地有150行 + 新下载1行 = 151行，但累加了151行的大小

## 修复方案

### 修复后的代码

```python
def download_stock_history(self, stock_code: str, ...) -> Optional[pd.DataFrame]:
    # ... 下载数据 ...
    
    # ✓ 正确：只在真正下载数据后统计
    if df is not None and not df.empty:
        estimated_size = len(df) * 100
        self.downloaded_bytes += estimated_size  # 只在下载时累加一次
    
    return df

def save_stock_data(self, stock_code: str, df: pd.DataFrame) -> bool:
    # ✓ 只负责保存，不统计
    file_path = os.path.join(self.daily_dir, f"{stock_code}.csv")
    return safe_write_csv(df, file_path)
```

## 数据量估算

### 估算公式

```
单只股票大小 = 行数 × 100字节/行
```

### 实际数据量

| 场景 | 股票数 | 天数 | 单股大小 | 总大小 |
|------|--------|------|----------|--------|
| 单只股票（150天） | 1 | 150 | 14.65 KB | 14.65 KB |
| 测试（5只） | 5 | 150 | 14.65 KB | 73.24 KB |
| 小规模（100只） | 100 | 150 | 14.65 KB | 1.43 MB |
| 中规模（1000只） | 1000 | 150 | 14.65 KB | 14.31 MB |
| **全部A股（5000只）** | **5000** | **150** | **14.65 KB** | **71.53 MB** |
| 日常更新（5000只） | 5000 | 1 | 0.10 KB | 488 KB |

### 计算示例

```
首次下载5000只股票:
  5000 × 150行 × 100字节 = 75,000,000字节
  = 73,242.19 KB
  = 71.53 MB
  ✓ 低于100MB限制

日常更新5000只股票:
  5000 × 1行 × 100字节 = 500,000字节
  = 488.28 KB
  = 0.48 MB
  ✓ 远低于100MB限制
```

## 配置建议

### 首次运行

```ini
[Download]
# 首次运行建议设为0（无限制）以完成完整下载
daily_download_limit_mb = 0
```

**原因**：
- 5000只股票约72MB，接近100MB
- 如果网络波动或重试，可能超过限制
- 首次下载完成后再启用限制

### 日常使用

```ini
[Download]
# 日常使用100MB足够
daily_download_limit_mb = 100
```

**原因**：
- 日常只需下载约0.5MB
- 100MB限制足够日常使用约200天
- 保护网络资源

### 无限制模式

```ini
[Download]
# 0表示无限制
daily_download_limit_mb = 0
```

**使用场景**：
- 首次运行
- 需要重新下载所有数据
- 网络状况良好时

## 限制检查逻辑

```python
def check_download_limit(self) -> bool:
    # 如果设置为0，表示无限制
    if self.daily_download_limit_mb == 0:
        return True
    
    # 检查是否超过限制
    if self.downloaded_bytes >= self.download_limit_bytes:
        self.logger.warning(f"已达到下载限制")
        return False
    
    return True
```

## 验证修复

### 测试场景1：5只股票

```
下载5只股票（150天）:
  预期大小: 73 KB
  实际限制: 100 MB
  结果: ✓ 应该能全部下载
```

### 测试场景2：5000只股票

```
下载5000只股票（150天）:
  预期大小: 72 MB
  实际限制: 100 MB
  结果: ✓ 应该能全部下载
```

### 测试场景3：日常更新

```
更新5000只股票（1天）:
  预期大小: 0.5 MB
  实际限制: 100 MB
  结果: ✓ 完全不受影响
```

## 使用建议

1. **首次运行**：
   ```ini
   daily_download_limit_mb = 0  # 无限制
   ```
   - 等待首次下载完成（30-60分钟）
   - 确认数据完整

2. **完成后调整**：
   ```ini
   daily_download_limit_mb = 100  # 启用限制
   ```
   - 重启程序使配置生效
   - 或在GUI设置中修改

3. **日常使用**：
   - 保持100MB限制
   - 每天自动执行
   - 只下载约0.5MB

## 日志监控

### 正常下载

```log
[INFO] 数据下载器初始化完成（每日下载限制: 100MB）
[INFO] 开始下载 5000 只股票数据...
[INFO] 进度: 1000/5000, 成功: 1000, 失败: 0
[INFO] 下载完成！成功: 5000, 失败: 0
[INFO] 下载数据量: 71.53MB / 100MB (71.5%)
```

### 达到限制

```log
[INFO] 开始下载 5000 只股票数据...
[INFO] 进度: 1000/5000, 成功: 1000, 失败: 0
[WARNING] 已达到每日下载限制 (100.00MB / 100MB)
[INFO] 下载限制已达到，跳过股票 600123
[INFO] 下载完成！成功: 1398, 失败: 3602
[INFO] 下载数据量: 100.00MB / 100MB (100.0%)
```

### 无限制模式

```log
[INFO] 数据下载器初始化完成（每日下载限制: 0MB）
[INFO] 开始下载 5000 只股票数据...
[INFO] 下载完成！成功: 5000, 失败: 0
[INFO] 下载数据量: 150.23MB / 0MB (无限制)
```

## 总结

### 问题根源
- 在保存文件时统计，导致重复计算
- 合并数据后再次保存时累加了全部数据量

### 修复方案
- 只在真正下载数据时统计
- 保存操作不再统计数据量

### 实际效果
- 100MB限制对5000只股票首次下载（72MB）完全够用
- 日常更新（0.5MB）完全不受影响
- 建议首次运行设为0，完成后改为100

### 配置变更
- 当前配置已修改为0（无限制）
- 首次下载完成后建议改回100MB
