# TradeAnalytics 微信推送功能 - 从这里开始

## 一句话说明

**让您的股票分析程序每天自动运行，并把结果推送到微信！**

## 效果展示

每天15:30，您的微信会收到这样的消息：

```
股票分析结果 2026-02-09

今日找到 8 只符合条件的股票
成交量≥5倍 且 价格>均线

近3日趋势：
- 今天：8只 📍
- 昨天：12只 📉  
- 前天：6只 📈

强势股（连续出现）：
• 603616 乐凯胶片
• 300666 江特电机

详情：
1. 603616 乐凯胶片 成交量×24.12
2. 300666 江特电机 成交量×12.61
...
```

## 三种方案，任选一种

### 方案1：Server酱（最简单，5分钟）

**特点**：免费、最简单、推送到微信

**步骤**：
1. 访问 https://sct.ftqq.com/ 获取SendKey
2. 编辑 `config/config.ini`，填入SendKey
3. 运行 `python test_push.py` 测试

**详细文档**：`QUICKSTART_PUSH.md`

---

### 方案2：企业微信（团队用，10分钟）

**特点**：免费、无限次、支持多人

**步骤**：
1. 注册企业微信
2. 创建群聊和机器人
3. 配置Webhook地址
4. 运行测试

**详细文档**：`WECHAT_PUSH_SETUP.md`

---

### 方案3：微信公众号（企业用，需认证）

**特点**：最专业、多用户、需300元/年

**步骤**：
1. 注册并认证服务号
2. 获取AppID、Secret、模板ID
3. 获取用户OpenID
4. 配置并测试

**详细文档**：`WECHAT_OFFICIAL_QUICKSTART.md`

---

## 配置Windows自动执行

配置完推送后，还需要设置定时执行：

**5分钟配置**：
1. 按 `Win+R`，输入 `taskschd.msc`
2. 创建基本任务
3. 每天15:30执行 `run_analysis.bat`

**详细文档**：`WINDOWS_SCHEDULER_SETUP.md`

## 完整文档列表

### 必读文档（推荐顺序）

1. **START_HERE.md**（本文档）- 从这里开始
2. **QUICKSTART_PUSH.md** - Server酱快速配置（5分钟）
3. **WINDOWS_SCHEDULER_SUMMARY.md** - Windows定时任务快速配置（5分钟）

### 进阶文档

- `PUSH_METHODS_COMPARISON.md` - 4种推送方案详细对比
- `WECHAT_PUSH_SETUP.md` - Server酱/企业微信/PushPlus详细配置
- `WECHAT_OFFICIAL_SETUP.md` - 微信公众号详细配置（23页）
- `WINDOWS_SCHEDULER_SETUP.md` - Windows定时任务详细配置（23页）

### 功能说明

- `WECHAT_PUSH_FEATURE.md` - 推送功能技术文档
- `STOCK_NAME_FIX.md` - 股票名称显示修复说明
- `WEEKEND_FIX.md` - 周末自动回退功能说明

## 测试工具

### 推送测试
```bash
python test_push.py
```

### 任务检查
```bash
check_task.bat
```

### 获取公众号关注者
```bash
python get_followers.py
```

### 检查公众号模板
```bash
python check_template.py
```

## 常见问题

### Q: 我应该选择哪个方案？

**个人用户** → Server酱
**团队用户** → 企业微信  
**企业应用** → 微信公众号

### Q: 配置需要多久？

- Server酱：5分钟
- 企业微信：10分钟
- 微信公众号：20分钟（不含认证等待时间）

### Q: 费用是多少？

- Server酱：免费（5次/天）
- 企业微信：完全免费
- 微信公众号：300元/年（认证费）

### Q: 可以推送给多人吗？

- Server酱：❌ 只能推送给自己
- 企业微信：✅ 推送到群里所有人
- 微信公众号：✅ 可配置多个用户

### Q: 如何修改执行时间？

编辑 `config/config.ini`：
```ini
[Scheduler]
run_time = 16:00  # 改为下午4点
```

## 已实现的功能

- ✅ 多种推送方式支持
- ✅ 自动定时执行
- ✅ 股票名称显示（不重复）
- ✅ 近3日趋势对比
- ✅ 连续强势股标记
- ✅ 周末自动回退数据
- ✅ 详细日志记录
- ✅ 错误自动重试

## 立即开始

### 最快路径（10分钟）

1. **配置推送**（5分钟）
   - 打开 `QUICKSTART_PUSH.md`
   - 按步骤配置Server酱
   - 运行 `python test_push.py`

2. **配置定时任务**（5分钟）
   - 打开 `WINDOWS_SCHEDULER_SUMMARY.md`
   - 创建Windows任务计划
   - 运行 `check_task.bat` 验证

3. **等待推送**
   - 明天15:30自动执行
   - 微信接收分析结果

## 技术支持

- 📖 查看相关文档
- 🧪 运行测试脚本
- 📝 查看日志文件（`logs/`目录）
- ❓ 查阅常见问题部分

---

**开始享受自动化股票分析吧！** 🚀📈
