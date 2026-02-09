# 微信推送快速上手（5分钟）

## 第一步：获取 SendKey（2分钟）

1. 用浏览器打开：https://sct.ftqq.com/
2. 微信扫码登录
3. 点击页面上的 "SendKey" 按钮
4. 复制显示的 SendKey（格式：`SCT***`开头的一长串字符）
5. 微信关注 "方糖气球" 服务号（会自动提示）

## 第二步：配置程序（2分钟）

1. 打开 `config/config.ini` 文件
2. 找到 `[Notification]` 部分
3. 修改为：

```ini
[Notification]
enabled = true
push_type = serverchan
serverchan_key = SCT你刚才复制的SendKey粘贴到这里
```

**示例**：
```ini
[Notification]
enabled = true
push_type = serverchan
serverchan_key = SCT123456ABCdefGHIjkl
```

4. 保存文件（`Ctrl+S`）

## 第三步：测试推送（1分钟）

在程序目录打开命令行，运行：

```bash
python test_push.py
```

如果显示"测试成功！"，几秒钟后你的微信会收到测试消息。

## 完成！

现在：
- 程序每天15:30自动执行分析
- 分析完成后自动推送结果到你的微信
- 无需任何手动操作

## 收到的消息示例

```
【股票分析结果 2026-02-09】

## 分析摘要
- 分析日期: 2026-02-09  
- 符合条件股票: 8 只
- 筛选条件: 成交量≥5倍 且 价格>均线

## 股票列表

### 1. 603616 乐凯胶片
- 日期: 2026-02-09
- 收盘价: 8.29元
- 均线: 5.72元  
- 成交量倍数: 24.12
- 价格高于均线: 44.93%

### 2. 300666 江特电机
...更多股票信息...
```

## 常见问题

**Q: 测试失败怎么办？**

A: 检查：
1. SendKey 复制完整，没有多余空格
2. `enabled = true` 这行没有注释符号 `#`
3. 网络连接正常

**Q: 如何停止推送？**

A: 将 `enabled = true` 改为 `enabled = false`

**Q: 推送次数限制？**

A: Server酱免费版每天5次，个人使用足够

**Q: 如何修改推送时间？**

A: 在 `config.ini` 的 `[Scheduler]` 部分修改 `run_time`：

```ini
[Scheduler]
run_time = 16:00  # 改为下午4点
```

## 更多配置

详细配置和其他推送方式（企业微信、PushPlus），请查看：`WECHAT_PUSH_SETUP.md`

## 问题反馈

如有问题，请检查：
1. `logs/` 目录下的日志文件
2. 运行 `python test_push.py` 查看详细错误信息
