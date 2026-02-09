# VIP群组推送配置指南

## 概述

将股票分析结果推送到企业微信VIP群组，只有群成员能够看到。

## 优势

- ✅ **完全免费** - 无任何费用
- ✅ **推送无限** - 不限次数
- ✅ **精准推送** - 只推送给VIP群组成员
- ✅ **支持多群** - 可以配置多个群（如VIP群、测试群）
- ✅ **格式丰富** - 支持Markdown、图片、链接
- ✅ **5分钟配置** - 超级简单

## 配置步骤（5分钟）

### 第一步：创建企业微信（如果还没有）

#### 方法1：个人注册（推荐）

1. 访问：https://work.weixin.qq.com/
2. 点击"企业注册"
3. 选择"其他企业"
4. 填写信息：
   - 企业名称：随便填（如"投资工作室"）
   - 行业：随便选
   - 人员规模：50人以下
5. 用手机号验证
6. 下载并安装"企业微信"APP

**个人完全可以免费注册！**

#### 方法2：使用现有企业微信

如果公司已有企业微信，直接使用即可。

### 第二步：创建VIP群组

1. 在企业微信APP中，创建一个群聊
2. 命名为"股票分析VIP群"（或任意名称）
3. 拉入需要接收推送的成员
4. 如果只有你自己，就只有你一个人的群

### 第三步：添加群机器人

1. 在群聊界面，点击右上角 **"..."**
2. 选择 **"群机器人"**
3. 点击 **"添加机器人"**
4. 给机器人起个名字：**"TradeAnalytics 分析助手"**
5. 点击"添加"
6. **复制 Webhook 地址**（非常重要！）

Webhook地址格式：
```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 第四步：配置程序

编辑 `config/config.ini`：

```ini
[Notification]
# 启用推送
enabled = true

# 使用企业微信
push_type = qywechat

# 粘贴VIP群的Webhook地址
qywechat_webhook = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key粘贴到这里

# 推送配置
push_history_days = 3  # 显示近3天趋势
push_max_stocks = 20   # 每次最多20只股票
```

### 第五步：测试推送

```bash
python test_push.py
```

如果配置正确，VIP群里会立即收到测试消息！

## 推送效果

### 群消息示例

```markdown
# 股票分析结果 2026-02-09

## 📊 今日摘要
- 分析日期: 2026-02-09
- 符合条件股票: **8 只**
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
- 日期: 2026-02-09
- 收盘价: 8.29元
- 均线: 5.72元
- 成交量倍数: **24.12**
- 价格高于均线: 44.93%

### 2. 300666 江特电机
- 日期: 2026-02-09
- 收盘价: 19.50元
- 均线: 15.82元
- 成交量倍数: **12.61**
- 价格高于均线: 23.26%

...更多股票信息...
```

### 消息特点

- ✅ **Markdown格式** - 排版美观，层次清晰
- ✅ **图标标识** - 📊📈⭐💎 一目了然
- ✅ **趋势分析** - 近3天数据对比
- ✅ **强势标记** - 自动识别连续股票
- ✅ **详细数据** - 价格、均线、倍数、涨幅

## 配置多个群组（已支持）

### 推送到多个群

如果有多个群（如VIP群、测试群、管理群），可以同时推送：

编辑 `config/config.ini`：

```ini
# 单个群
qywechat_webhook = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=VIP群的key

# 多个群（用逗号分隔）
qywechat_webhook = https://qyapi.weixin.qq.com/.../key1,https://qyapi.weixin.qq.com/.../key2

# 也支持用分号分隔
qywechat_webhook = https://qyapi.weixin.qq.com/.../key1;https://qyapi.weixin.qq.com/.../key2
```

**示例：推送到VIP群和测试群**

```ini
qywechat_webhook = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc123,https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=def456
```

程序会自动向每个群发送消息。

### 群组分类建议

1. **VIP群** - 正式成员，接收所有推送
2. **测试群** - 测试人员，验证功能
3. **管理群** - 管理员，查看系统状态

### 配置示例

```ini
# 同时推送到3个群
qywechat_webhook = https://qyapi.weixin.qq.com/.../VIP群key,https://qyapi.weixin.qq.com/.../测试群key,https://qyapi.weixin.qq.com/.../管理群key
```

**注意**：Webhook地址较长，建议分行编辑后合并成一行。

## 群成员管理

### 添加VIP成员

1. 在群聊中点击 **"+"**
2. 选择要添加的成员
3. 添加后，成员会自动收到推送

### 移除成员

1. 在群聊中点击 **"..."**
2. 选择 **"群成员"**
3. 找到要移除的成员，点击移除

### 设置群权限

可以设置：
- 谁可以添加成员
- 谁可以@所有人
- 是否允许普通成员发言

建议：设置为"仅群主和管理员可发言"，保持群的专注性。

## 安全建议

### 1. Webhook安全

- ⚠️ **不要分享Webhook地址** - 任何人有这个地址都能往群里发消息
- ✅ **定期更换** - 如果泄露，删除机器人重新创建
- ✅ **不要上传到公开仓库** - config.ini不要提交到GitHub

### 2. 群组管理

- ✅ 只邀请信任的成员
- ✅ 定期清理不活跃成员
- ✅ 设置合理的群权限

### 3. 推送内容

- ✅ 不推送敏感个人信息
- ✅ 仅推送公开市场数据
- ✅ 添加免责声明（可选）

## 高级功能

### 1. @特定成员

如果需要@特定VIP成员，可以在推送内容中添加：

```python
# 在 src/notification.py 中修改
content = f"@所有人\n\n{content}"  # @所有人
# 或
content = f"<@userid>\n\n{content}"  # @特定成员
```

### 2. 发送图片

企业微信支持发送图片：

```python
# 可以发送K线图到群里
def send_chart_to_group(webhook, image_path):
    # 实现图片上传和发送
    ...
```

### 3. 消息类型

企业微信支持多种消息类型：
- **Markdown** - 当前使用，排版好
- **文本** - 纯文本
- **图片** - 发送图表
- **图文** - 带链接的卡片
- **文件** - 发送Excel文件

### 4. 条件推送

可以设置只在特定条件下推送：

```ini
# 只在找到超过5只股票时推送
push_min_stocks = 5

# 只在成交量倍数超过10时推送
push_min_volume_ratio = 10
```

## Windows定时任务设置

配置完推送后，设置自动执行：

### 快速方法

1. 按 `Win+R`，输入：`taskschd.msc`
2. 创建基本任务：
   - 名称：`TradeAnalytics VIP群推送`
   - 触发器：每天 15:30
   - 操作：启动 `run_analysis.bat`
3. 完成！

详细说明：`WINDOWS_SCHEDULER_SUMMARY.md`

## 测试清单

- [ ] 创建企业微信和VIP群
- [ ] 添加群机器人并获取Webhook
- [ ] 配置 config.ini
- [ ] 运行 `python test_push.py` 测试
- [ ] 群里收到测试消息
- [ ] 配置Windows定时任务
- [ ] 运行 `check_task.bat` 验证

## 常见问题

### Q1: 可以创建多个VIP群吗？

**可以！** 但需要获取每个群的Webhook地址。

**配置方法**：
目前支持单个群，如需多群推送，我可以帮您修改代码。

### Q2: 非VIP成员能看到消息吗？

**不能**。只有群成员能看到群机器人的消息。

### Q3: 个人可以使用企业微信吗？

**完全可以！** 个人可以免费注册企业微信，创建自己的"企业"。

### Q4: 群成员需要安装企业微信吗？

**需要**。群成员需要：
1. 下载企业微信APP
2. 加入你的企业
3. 进入VIP群

### Q5: 可以同时推送到VIP群和个人微信吗？

**可以**，但需要修改代码支持多个推送目标。我可以帮您实现。

### Q6: 如何临时停止推送？

编辑 config.ini：
```ini
enabled = false  # 改为false即可
```

## 与其他方案对比

| 特性 | 企业微信VIP群 | Server酱 | 微信公众号 |
|------|--------------|----------|------------|
| 费用 | 免费 | 免费 | 300元/年 |
| 推送对象 | VIP群成员 | 仅自己 | 配置的用户 |
| 推送次数 | 无限 | 5次/天 | 无限 |
| 群组聊天 | ✅ | ❌ | ❌ |
| 个人可用 | ✅ | ✅ | ❌（需企业） |

**VIP群组方案的独特优势**：
- 群成员可以互相交流
- 可以@特定成员
- 可以发送图片、文件
- 完全免费

## 推送时间建议

```ini
[Scheduler]
run_time = 15:30  # 收盘后30分钟
# 或
run_time = 16:00  # 收盘后1小时（数据更稳定）
```

建议选择15:30-16:00之间，此时：
- 交易已结束
- 数据基本稳定
- VIP成员有时间查看

## 下一步

1. ✅ 按照本文档配置企业微信VIP群
2. ✅ 运行 `python test_push.py` 测试
3. ✅ 配置Windows定时任务（见 WINDOWS_SCHEDULER_SUMMARY.md）
4. ✅ 等待明天15:30自动推送到VIP群

## 完整配置示例

```ini
[Scheduler]
enabled = true
run_time = 15:30
weekdays_only = true

[Notification]
enabled = true
push_type = qywechat
qywechat_webhook = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的VIP群key
push_history_days = 3
push_max_stocks = 20
```

## 测试命令

```bash
# 测试推送
python test_push.py

# 检查定时任务
check_task.bat
```

---

**配置完成后，VIP群成员每天都能自动收到最新的股票分析结果！** 🎯
