# 微信推送功能使用指南

## 快速选择

### 我是个人用户，只推送给自己
👉 **使用 Server酱**
- 配置时间：5分钟
- 查看：`QUICKSTART_PUSH.md`

### 我是团队，需要多人接收
👉 **使用 企业微信**
- 配置时间：10分钟
- 查看：`WECHAT_PUSH_SETUP.md`

### 我有企业资质，要正式应用
👉 **使用 微信公众号**
- 配置时间：20分钟 + 认证
- 查看：`WECHAT_OFFICIAL_QUICKSTART.md`

## 三步配置（以Server酱为例）

### 1. 获取SendKey
访问：https://sct.ftqq.com/

### 2. 配置程序
编辑 `config/config.ini`：
```ini
[Notification]
enabled = true
push_type = serverchan
serverchan_key = SCT你的Key
```

### 3. 测试推送
```bash
python test_push.py
```

## 推送效果预览

每天15:30，你会收到这样的消息：

```markdown
【股票分析结果 2026-02-09】

## 📊 今日摘要
- 符合条件股票: 8 只
- 筛选条件: 成交量≥5倍 且 价格>均线

## 📈 近3日趋势  
- 📍 2026-02-09: 8 只
- 📉 2026-02-08: 12 只
- 📈 2026-02-07: 6 只

## ⭐ 连续出现股票（强势）
- 603616 乐凯胶片
- 300666 江特电机

## 💎 今日股票列表

### 1. 603616 乐凯胶片
- 收盘价: 8.29元
- 成交量倍数: **24.12**
- 价格高于均线: 44.93%

### 2. 300666 江特电机
- 收盘价: 19.50元
- 成交量倍数: **12.61**
- 价格高于均线: 23.26%

...更多股票信息...
```

## 文档索引

### 快速上手
- `QUICKSTART_PUSH.md` - Server酱5分钟配置
- `WECHAT_OFFICIAL_QUICKSTART.md` - 公众号10分钟配置

### 详细配置
- `WECHAT_PUSH_SETUP.md` - Server酱/企业微信/PushPlus完整配置
- `WECHAT_OFFICIAL_SETUP.md` - 微信公众号完整配置

### 对比参考
- `PUSH_METHODS_COMPARISON.md` - 4种方案详细对比

### Windows定时任务
- `WINDOWS_SCHEDULER_SETUP.md` - 完整配置指南
- `WINDOWS_SCHEDULER_SUMMARY.md` - 快速参考

## 辅助脚本

### 测试脚本
- `test_push.py` - 测试推送功能
- `check_task.bat` - 检查Windows任务状态

### 公众号专用
- `get_followers.py` - 获取公众号关注者
- `check_template.py` - 检查模板配置

### 启动脚本
- `run_analysis.bat` - 任务计划程序使用
- `start_background.bat` - 后台常驻运行

## 完整工作流程

```
定时触发（每天15:30）
    ↓
run_analysis.bat
    ↓
main.py 执行分析
    ↓
1. 更新股票列表
2. 下载最新数据
3. 筛选符合条件股票
4. 保存结果文件
    ↓
生成推送内容
- 今日结果
- 近3日趋势
- 连续强势股
    ↓
发送微信推送
- Server酱 → 微信服务号
- 企业微信 → 企业微信群
- 微信公众号 → 公众号模板消息
    ↓
用户收到通知
    ↓
等待下次执行
```

## 故障排查

### 1. 推送未收到

**检查清单**：
- [ ] config.ini 中 `enabled = true`
- [ ] 密钥/Token配置正确
- [ ] 网络连接正常
- [ ] 运行 `test_push.py` 测试

### 2. 测试失败

**查看日志**：
```bash
type logs\notification.log
```

**常见错误**：
- SendKey错误 → 重新复制
- OpenID错误 → 重新获取
- 网络超时 → 检查网络

### 3. 定时任务未执行

**检查方法**：
```bash
check_task.bat
```

**查看日志**：
```bash
type logs\scheduler.log
```

## 下一步

1. ✅ 选择适合的推送方案
2. ✅ 按照对应文档配置（5-20分钟）
3. ✅ 运行 `test_push.py` 测试
4. ✅ 配置Windows定时任务
5. ✅ 等待明天15:30自动推送

## 技术支持

如遇问题：
1. 查看对应的配置文档
2. 运行测试脚本诊断
3. 查看日志文件
4. 检查网络连接

---

**祝您使用愉快！📈**
