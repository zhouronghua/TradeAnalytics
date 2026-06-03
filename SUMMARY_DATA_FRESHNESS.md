# 数据时效性改进 - 快速总结

## 问题
之前可能推送几个月前的旧数据，让用户收到过期的股票信息。

## 解决方案
✅ 只推送**最近2天**的数据  
✅ 没有最近数据时发送**空通知**  
✅ 明确日志说明数据日期范围  

## 立即使用

### 正常运行（自动过滤旧数据）

```bash
# 直接运行，会自动过滤超过2天的数据
python src/volume_analyzer.py
```

### 测试验证

```bash
# 运行时效性测试
python test_data_freshness.py
```

## 预期结果

### 有最近数据时
```
[INFO] 找到 15 只符合条件的股票（最近2天）
[INFO] 数据日期范围: 2026-06-02 至 2026-06-03
[INFO] 邮件发送成功
[INFO] 方糖推送成功
```

### 无最近数据时
```
[INFO] 未找到符合条件的股票（仅统计最近2天的数据）
[INFO] 注意：如果数据未更新，不会推送历史数据
[INFO] 已发送空结果邮件
[INFO] 已发送空结果方糖推送
```

## 推送内容示例

### 有股票时
```
选股 2026-06-03 MA20 量比>=5.0 | 15只

今日摘要
- 分析日期: 2026-06-03
- 符合条件股票: 15 只
- 数据日期: 最近2天

股票列表
1. 600000 浦发银行 ...
```

### 无股票时
```
选股 2026-06-03 MA20 量比>=5.0 | 无符合标的

今日摘要
- 分析日期: 2026-06-03
- 符合条件股票: 0 只

分析结果
今日未发现符合条件的股票。

注意: 仅统计最近2天的数据，不会推送历史数据。
```

## 配置说明

### 默认配置（推荐）
```python
# 保留最近2天的数据
max_days_old = 2
```

### 自定义配置
如需修改，编辑 `src/volume_analyzer.py` 中的 `run_batch_analysis` 方法：

```python
results_df = analyze_volume_surge(
    csv_files,
    max_days_old=1,  # 改为只保留当天
)
```

建议：
- `max_days_old=1` - 只要当天（严格）
- `max_days_old=2` - **推荐**（考虑T+1延迟）
- `max_days_old=3` - 保留3天（宽松）

## Crontab 建议

### 下午运行（推荐）
```bash
# 每个交易日下午3:30
30 15 * * 1-5 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
```

### 次日早上运行
```bash
# 每个交易日次日早上9:00
0 9 * * 2-6 cd /path/to/TradeAnalytics && python src/volume_analyzer.py
```

## 常见问题

### Q: 为什么是2天而不是1天？
A: 考虑T+1数据延迟和周末节假日，2天更合理。

### Q: 如何关闭空通知？
A: 使用 `--no-email --no-notification` 参数：
```bash
python src/volume_analyzer.py --no-email --no-notification
```

### Q: 如何验证数据是最新的？
A: 查看日志中的"数据日期范围"信息：
```
[INFO] 数据日期范围: 2026-06-02 至 2026-06-03
```

## 测试步骤

```bash
# 1. 运行时效性测试
python test_data_freshness.py

# 2. 运行实际分析
python src/volume_analyzer.py

# 3. 检查日志
tail -f logs/*.log

# 4. 查看推送消息（邮件或方糖）
```

## 相关文档

- [DATA_FRESHNESS_UPDATE.md](DATA_FRESHNESS_UPDATE.md) - 详细的技术文档
- [VOLUME_ANALYZER_QUICKSTART.md](VOLUME_ANALYZER_QUICKSTART.md) - 完整使用指南
- [DOCS_INDEX.md](DOCS_INDEX.md) - 文档索引

## 总结

这次改进确保了：

✅ **不会推送旧数据** - 只保留最近2天  
✅ **明确反馈** - 无数据时发送空通知  
✅ **日志清晰** - 显示数据日期范围  
✅ **T+1兼容** - 考虑数据延迟  

现在可以放心地添加到 crontab，不用担心收到过期信息！
