# VIP群组推送 - 功能总结

## 已完成功能

### 1. 核心推送功能

- ✅ **企业微信VIP群推送** - 主推方案
- ✅ **多群同时推送** - 支持同时推送到多个群
- ✅ **推送内容丰富** - 今日结果+历史趋势+强势股
- ✅ **Markdown格式** - 排版美观，图标清晰
- ✅ **智能筛选** - 只推送有价值的信息

### 2. 推送内容模块

#### 📊 今日摘要
- 分析日期
- 符合条件股票数量
- 筛选规则说明

#### 📈 近N日趋势
- 可配置显示天数（默认3天）
- 趋势图标标识（📈上升 📉下降 ➡️持平）
- 帮助判断市场热度变化

#### ⭐ 连续强势股
- 自动识别连续出现的股票
- 这些股票势头强劲，重点关注
- 按出现次数排序

#### 💎 今日股票详情
- 股票代码和名称
- 收盘价、均线价格
- 成交量倍数（核心指标）
- 价格相对均线涨幅
- 按成交量倍数降序排列

### 3. 配置管理

#### 推送开关
```ini
[Notification]
enabled = true/false  # 一键开关
```

#### 推送类型
- `qywechat` - 企业微信（推荐）
- `serverchan` - Server酱
- `pushplus` - PushPlus
- `wechat_official` - 微信公众号

#### 多群配置
```ini
# 单个群
qywechat_webhook = webhook1

# 多个群（逗号分隔）
qywechat_webhook = webhook1,webhook2,webhook3

# 多个群（分号分隔）
qywechat_webhook = webhook1;webhook2;webhook3
```

#### 内容配置
```ini
push_history_days = 3   # 历史趋势天数
push_max_stocks = 20    # 最多推送股票数
```

### 4. 自动化执行

#### Windows任务计划
- ✅ 配置脚本：`run_analysis.bat`
- ✅ 检查脚本：`check_task.bat`
- ✅ 后台启动：`start_background.bat`
- ✅ 默认时间：每天15:30（收盘后30分钟）
- ✅ 工作日执行（周末跳过）

#### 执行流程
```
1. 下载最新数据
2. 筛选符合条件股票
3. 执行成交量分析
4. 生成推送内容
5. 推送到VIP群
6. 记录日志
```

### 5. 测试和验证

#### 测试脚本
- `test_push.py` - 测试推送功能
- 自动检测配置
- 显示详细错误信息
- 支持所有推送类型

#### 验证工具
- `check_task.bat` - 检查定时任务状态
- 显示任务配置
- 显示最近日志
- 显示执行历史

### 6. 完整文档

#### 快速入门
- ✅ `VIP_GROUP_QUICKSTART.md` - 3分钟快速配置
- ✅ `START_HERE.md` - 总入口文档

#### 详细说明
- ✅ `VIP_GROUP_PUSH_SETUP.md` - 企业微信详细配置
- ✅ `README_VIP_PUSH.md` - 完整功能说明
- ✅ `WINDOWS_SCHEDULER_SUMMARY.md` - Windows定时任务

#### 对比参考
- ✅ `PUSH_METHODS_COMPARISON.md` - 各种推送方式对比

## 技术实现

### 核心模块

#### 1. NotificationService（src/notification.py）

**主要功能**：
- 管理各种推送方式
- 格式化推送内容
- 读取历史分析结果
- 识别连续强势股

**关键方法**：
```python
def send_analysis_result(stocks, analysis_date):
    """发送分析结果"""
    
def _send_qywechat(title, content):
    """企业微信推送（支持多群）"""
    
def _format_stocks_content(stocks):
    """格式化股票内容（含历史趋势）"""
    
def _get_history_results():
    """获取历史分析结果"""
    
def _find_continuous_stocks(today_stocks, history):
    """识别连续出现的强势股"""
```

**企业微信多群支持**：
```python
# 自动分割Webhook（支持逗号、分号分隔）
webhooks = qywechat_webhook.split(',')

# 向每个群推送
for webhook in webhooks:
    response = requests.post(webhook, json=data)
    
# 只要有一个成功即返回True
```

#### 2. TaskScheduler（src/scheduler.py）

**集成推送**：
```python
# 分析完成后自动推送
if matched_stocks:
    push_success = self.notifier.send_analysis_result(
        matched_stocks, analysis_date
    )
```

### 数据流

```
1. 数据源（BaoStock）
   ↓
2. 数据下载器（DataDownloader）
   ↓
3. 成交量分析（VolumeAnalyzer）
   ↓
4. 结果筛选（StockFilter）
   ↓
5. 任务调度器（TaskScheduler）
   ↓
6. 通知服务（NotificationService）
   ↓
7. 企业微信VIP群
```

### 配置文件结构

```ini
config/config.ini
├── [Scheduler]      # 定时任务配置
├── [Data]           # 数据源配置
├── [Analysis]       # 分析参数配置
├── [Filter]         # 筛选规则配置
└── [Notification]   # 推送配置（新增）
    ├── enabled
    ├── push_type
    ├── qywechat_webhook      # 支持多群
    ├── serverchan_key
    ├── pushplus_token
    ├── wechat_appid
    ├── wechat_secret
    ├── wechat_template_id
    ├── wechat_openids
    ├── push_history_days
    └── push_max_stocks
```

## 使用场景

### 场景1：个人投资者

**需求**：自己查看分析结果

**配置**：
- 创建个人企业微信（免费）
- 创建1个群（只有自己）
- 每天收到推送
- 费用：0元

### 场景2：投资团队（5-10人）

**需求**：团队成员共享分析结果

**配置**：
- 创建VIP群（团队成员）
- 1个Webhook
- 所有成员同时收到
- 可以在群里讨论
- 费用：0元

### 场景3：投资工作室（多群）

**需求**：
- VIP客户群（付费客户）
- 内部讨论群（员工）
- 测试验证群（测试）

**配置**：
```ini
qywechat_webhook = VIP群webhook,内部群webhook,测试群webhook
```
- 同时推送到3个群
- 不同群看到相同内容
- 费用：0元

### 场景4：分级推送（待实现）

**需求**：不同群推送不同内容

**示例**：
- VIP群：推送所有股票
- 普通群：只推送成交量>10倍的股票

**实现**：需要修改代码，根据Webhook区分推送内容

## 优势总结

### 与其他方案对比

| 特性 | 企业微信VIP群 | Server酱 | 微信公众号 |
|------|--------------|----------|------------|
| 费用 | 免费 | 免费 | 300元/年认证 |
| 推送次数 | 无限 | 5次/天（免费） | 无限 |
| 推送对象 | VIP群成员 | 仅自己 | 配置的用户 |
| 群聊功能 | ✅ | ❌ | ❌ |
| 配置难度 | 简单 | 极简 | 复杂 |
| 个人可用 | ✅ | ✅ | ❌（需企业资质） |
| 多人分享 | ✅ | ❌ | ✅ |
| 图片支持 | ✅ | ❌ | ✅ |
| 富文本 | Markdown | Markdown | 模板消息 |

### 企业微信的独特优势

1. **完全免费** - 无任何费用
2. **推送无限** - 不限次数
3. **多人共享** - VIP群所有成员
4. **群聊互动** - 可以讨论交流
5. **多群支持** - 同时推送多个群
6. **简单配置** - 3分钟即可完成
7. **个人可用** - 个人免费注册企业微信

## 安全和隐私

### 1. Webhook安全

- ⚠️ **不要分享** - Webhook相当于群的钥匙
- ⚠️ **不要上传** - config.ini不要提交到公开仓库
- ✅ **泄露处理** - 删除机器人重新创建

### 2. 推送内容

- ✅ 仅推送公开市场数据
- ✅ 不包含个人隐私信息
- ✅ 建议添加免责声明

### 3. VIP群管理

- ✅ 只邀请信任的成员
- ✅ 定期审查成员列表
- ✅ 设置合理的群权限

## 扩展功能（可选）

### 1. 条件推送

只在特定条件下推送：

```python
# 只有找到超强势股票才推送
if max(stock['volume_ratio'] for stock in stocks) > 20:
    service.send_analysis_result(stocks)
```

### 2. @特定成员

重要股票@特定成员：

```python
content = f"<@某个成员的userid>\n\n{content}"
```

### 3. 图表推送

将K线图也发送到群：

```python
# 生成图表
chart_path = generate_chart(stock_code)

# 上传并发送
send_image_to_group(webhook, chart_path)
```

### 4. 周报月报

除了每日推送，还可以：
- 每周五晚上推送本周总结
- 每月末推送月度总结

### 5. 智能提醒

根据市场情况智能提醒：
- 暴涨股票立即提醒
- 连续3天强势提醒
- 市场异常波动提醒

## 常见问题

### Q1: 企业微信个人可以注册吗？

**可以！** 访问 https://work.weixin.qq.com/ 免费注册，选择"其他企业"即可。

### Q2: 推送失败怎么办？

1. 检查Webhook是否完整
2. 运行 `python test_push.py` 测试
3. 查看日志：`logs/notification.log`
4. 确认机器人未被删除

### Q3: 可以推送到多少个群？

理论上无限，建议不超过5个群（性能考虑）。

### Q4: 非VIP成员能看到推送吗？

**不能**。只有群成员能看到群机器人的消息。

### Q5: 可以修改推送内容吗？

可以！修改 `src/notification.py` 中的 `_format_stocks_content()` 方法。

### Q6: 如何临时停止推送？

```ini
[Notification]
enabled = false  # 设置为false即可
```

## 测试清单

使用前请完成以下测试：

- [ ] 企业微信注册并登录
- [ ] 创建VIP群
- [ ] 添加群机器人
- [ ] 复制Webhook地址
- [ ] 配置config.ini
- [ ] 运行 `python test_push.py`
- [ ] VIP群收到测试消息
- [ ] 配置Windows定时任务
- [ ] 运行 `check_task.bat` 验证
- [ ] 等待第一次自动推送

## 快速链接

### 配置文档
- **VIP_GROUP_QUICKSTART.md** - 最快速的配置指南
- **VIP_GROUP_PUSH_SETUP.md** - 详细配置说明
- **README_VIP_PUSH.md** - 完整功能说明
- **WINDOWS_SCHEDULER_SUMMARY.md** - 定时任务配置

### 测试和检查
```bash
# 测试推送
python test_push.py

# 检查定时任务
check_task.bat

# 查看日志
type logs\notification.log
```

### 在线资源
- 企业微信注册：https://work.weixin.qq.com/
- 企业微信API文档：https://developer.work.weixin.qq.com/

---

## 总结

**VIP群组推送功能已完整实现！**

- ✅ 核心功能完善（推送、格式化、多群）
- ✅ 配置简单（3分钟）
- ✅ 文档齐全（快速配置+详细说明）
- ✅ 测试充分（test_push.py + check_task.bat）
- ✅ 完全免费（0成本）
- ✅ 推送无限（无限制）

**立即开始：VIP_GROUP_QUICKSTART.md** 🚀
