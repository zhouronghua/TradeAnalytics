# 微信公众号推送快速配置

## 前提条件

- ✅ 已注册微信公众号（服务号）
- ✅ 已完成认证（300元/年）
- ✅ 已获取AppID和AppSecret

**个人用户注意**：个人无法注册服务号，建议使用：
- Server酱（推荐，5分钟配置）
- 企业微信（免费，功能强大）

## 配置步骤（10分钟）

### 步骤1：获取AppID和Secret（2分钟）

1. 登录公众号后台：https://mp.weixin.qq.com/
2. 点击"设置与开发" → "基本配置"
3. 记录**AppID**（开发者ID）
4. 点击"重置"生成**AppSecret**（注意：只显示一次！）

### 步骤2：添加模板消息（3分钟）

1. 点击"功能" → "模板消息"
2. 点击"模板库"
3. 搜索："数据统计通知"或"服务提醒"
4. 点击"详情"→"选用"
5. 记录**模板ID**

推荐模板：
- 数据统计通知
- 行情提醒
- 服务提醒

### 步骤3：配置程序（2分钟）

编辑 `config/config.ini`：

```ini
[Notification]
# 启用推送
enabled = true

# 使用微信公众号
push_type = wechat_official

# 填写你的配置
wechat_appid = wx你的AppID
wechat_secret = 你的AppSecret粘贴到这里
wechat_template_id = 你的模板ID

# OpenID先留空，下一步获取
wechat_openids = 
```

### 步骤4：获取用户OpenID（3分钟）

#### 方法1：自动获取（推荐）

1. 用微信关注你的公众号
2. 运行脚本：

```bash
python get_followers.py
```

3. 脚本会显示所有关注者的OpenID
4. 复制OpenID，填入配置文件

#### 方法2：手动查看

1. 公众号后台 → "用户管理"
2. 找到你的用户，查看OpenID
3. 复制填入配置文件

**配置示例**：

```ini
# 推送给单个用户
wechat_openids = oXXXXXXXXXXXXXXXXXXXXXXXXXX

# 推送给多个用户（用逗号分隔）
wechat_openids = oXXXX...,oYYYY...,oZZZZ...
```

### 步骤5：测试推送（1分钟）

```bash
python test_push.py
```

如果配置正确，你的微信会收到测试消息！

## 推送效果

### 消息示例

```
【TradeAnalytics 测试消息】

日期：2026-02-09
符合条件：8只
趋势：今日 8只 ↑

股票列表：
1. 603616 乐凯胶片 (×24.1)
2. 300666 江特电机 (×12.6)
3. 002462 嘉事堂 (×10.3)
...共8只

成交量≥5倍 且 价格>均线
点击查看详情
```

### 点击效果

可以配置点击后跳转到：
- 公众号文章
- H5页面
- 小程序
- 外部链接

## 常见问题

### Q1: 推送失败："用户未关注公众号"

**原因**：OpenID对应的用户未关注或已取消关注

**解决**：
1. 确认用户已关注公众号
2. 重新运行 `get_followers.py` 获取最新列表

### Q2: 推送失败："模板ID无效"

**原因**：模板ID配置错误

**解决**：
1. 运行 `python check_template.py` 查看所有模板
2. 复制正确的模板ID到配置文件

### Q3: 获取AccessToken失败

**原因**：AppID或Secret配置错误

**解决**：
1. 检查AppID是否正确（以wx开头）
2. 重新生成AppSecret
3. 确认没有多余的空格

### Q4: 如何推送给多个用户？

在配置文件中用逗号分隔：

```ini
wechat_openids = oUser1,oUser2,oUser3
```

程序会自动推送给所有配置的用户。

### Q5: 个人如何使用公众号推送？

个人无法申请服务号，建议：

**方案1：Server酱（推荐）**
- 完全免费
- 5分钟配置
- 推送到微信服务号
- 详见：QUICKSTART_PUSH.md

**方案2：企业微信**
- 免费
- 推送无限制
- 可以个人注册

**方案3：使用朋友的企业公众号**
- 让有企业资质的朋友注册
- 添加你为管理员

## 辅助工具

### get_followers.py
获取所有关注者的OpenID列表

```bash
python get_followers.py
```

### check_template.py
检查模板消息配置

```bash
python check_template.py
```

### test_push.py
测试推送功能

```bash
python test_push.py
```

## 费用说明

- 认证费：300元/年（必需）
- 推送费用：完全免费
- 推送次数：无限制

## 与Server酱对比

| 特性 | Server酱 | 微信公众号 |
|------|----------|------------|
| 费用 | 免费 | 300元/年 |
| 配置难度 | 简单（5分钟） | 中等（10分钟） |
| 推送次数 | 5次/天 | 无限 |
| 用户限制 | 单用户 | 多用户 |
| 消息格式 | Markdown | 模板 |
| 企业要求 | 无 | 需要企业资质 |

## 推荐选择

- **个人用户**：Server酱（最简单）
- **小团队**：企业微信（免费+多用户）
- **正式应用**：微信公众号（最专业）

## 下一步

1. ✅ 配置完成后运行 `test_push.py` 测试
2. ✅ 配置Windows定时任务（见 WINDOWS_SCHEDULER_SETUP.md）
3. ✅ 等待每天15:30自动推送

---

**详细配置说明**：WECHAT_OFFICIAL_SETUP.md（完整文档）
