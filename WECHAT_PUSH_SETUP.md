# 微信推送配置指南

## 功能说明

程序支持在每日分析任务完成后，自动将结果推送到您的微信。支持多种推送方式：
- **Server酱**（推荐）：推送到微信服务号
- **企业微信机器人**：推送到企业微信群
- **PushPlus**：推送到微信服务号（备选）

## 方案1：Server酱（推荐，最简单）

### 优点
- 完全免费
- 配置简单，5分钟搞定
- 推送到微信服务号，像收到公众号消息一样
- 每天免费推送5次（足够个人使用）

### 配置步骤

#### 1. 获取SendKey

1. 访问 Server酱官网：https://sct.ftqq.com/
2. 使用微信扫码登录
3. 点击"SendKey" - 复制你的SendKey（格式：`SCT***`）
4. 关注"方糖气球"微信服务号（自动关注）

#### 2. 配置程序

编辑 `config/config.ini` 文件：

```ini
[Notification]
# 启用推送
enabled = true
# 使用Server酱
push_type = serverchan
# 填入你的SendKey
serverchan_key = SCT你的SendKey这里
```

#### 3. 测试推送

运行测试命令：

```bash
python src/notification.py
```

如果配置正确，你的微信会收到一条测试消息。

### 推送示例

收到的消息内容：

```
【股票分析结果 2026-02-09】

## 分析摘要
- 分析日期: 2026-02-09
- 符合条件股票: 15 只
- 筛选条件: 成交量≥5倍 且 价格>均线

## 股票列表

### 1. 603616 乐凯胶片
- 日期: 2026-02-09
- 收盘价: 8.29元
- 均线: 5.72元
- 成交量倍数: 24.12
- 价格高于均线: 44.93%

### 2. 300666 江特电机
...
```

## 方案2：企业微信机器人

### 优点
- 完全免费
- 不限推送次数
- 支持Markdown格式

### 缺点
- 需要企业微信（个人可免费注册）
- 消息发送到群里，不是私聊

### 配置步骤

#### 1. 创建企业微信

1. 访问：https://work.weixin.qq.com/
2. 注册企业微信（个人可使用）
3. 创建一个内部群

#### 2. 添加机器人

1. 在群聊中点击右上角"..."
2. 选择"群机器人"
3. 点击"添加机器人"
4. 复制Webhook地址

#### 3. 配置程序

编辑 `config/config.ini`：

```ini
[Notification]
enabled = true
push_type = qywechat
qywechat_webhook = https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key
```

## 方案3：PushPlus（备选）

### 配置步骤

1. 访问：http://www.pushplus.plus/
2. 使用微信扫码登录
3. 复制你的Token
4. 配置：

```ini
[Notification]
enabled = true
push_type = pushplus
pushplus_token = 你的token
```

## 自动执行设置

### 1. 启用定时任务

编辑 `config/config.ini`：

```ini
[Scheduler]
enabled = true
# 每天15:30执行（收盘后）
run_time = 15:30
# 只在工作日执行
weekdays_only = true
```

### 2. 启动程序

#### Windows

创建 `start.bat`：

```batch
@echo off
python main.py
```

双击运行，程序会在后台等待，每天15:30自动执行分析并推送。

#### Linux/Mac

创建 `start.sh`：

```bash
#!/bin/bash
python3 main.py
```

或使用 systemd 服务、crontab 等方式开机自动启动。

### 3. 设置开机自启动（Windows）

1. 按 `Win+R`，输入 `shell:startup`
2. 将 `start.bat` 的快捷方式放到这个文件夹
3. 重启电脑，程序自动启动

### 4. 使用计划任务（推荐）

**Windows任务计划程序**：

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：开机时
4. 操作：启动程序
5. 程序：`python`
6. 参数：`main.py`
7. 起始位置：程序所在目录

## 推送内容说明

程序会推送：
- 分析日期
- 符合条件的股票数量
- 每只股票的详细信息：
  - 股票代码和名称
  - 收盘价
  - 均线
  - 成交量倍数
  - 价格相对均线的涨幅

最多推送前20只股票，避免消息过长。

## 常见问题

### Q: 没有收到推送？

A: 检查以下几点：
1. `config.ini` 中 `enabled = true`
2. SendKey/Token 配置正确
3. 运行测试命令确认配置
4. 查看日志文件 `logs/` 了解详情

### Q: 推送频率限制？

A: 
- Server酱：免费版每天5次
- 企业微信：无限制
- PushPlus：每天200次

### Q: 如何只在找到股票时推送？

A: 程序已自动处理，如果没有符合条件的股票，不会发送推送。

### Q: 如何自定义推送内容？

A: 修改 `src/notification.py` 中的 `_format_stocks_content` 方法。

### Q: 支持同时推送到多个平台吗？

A: 当前不支持，但可以通过修改代码实现。未来版本会考虑添加。

## 安全建议

1. 不要将 SendKey/Token 上传到 GitHub 等公开仓库
2. 定期更换 SendKey/Token
3. 不要分享你的 SendKey/Token 给他人

## 技术支持

如果遇到问题：
1. 查看 `logs/` 目录下的日志文件
2. 运行测试命令：`python src/notification.py`
3. 检查配置文件格式是否正确

## 升级说明

已添加的文件：
- `src/notification.py` - 推送服务模块
- `WECHAT_PUSH_SETUP.md` - 本配置文档

已修改的文件：
- `config/config.ini` - 添加推送配置
- `src/scheduler.py` - 集成推送功能

现有功能不受影响，如不需要推送功能，保持 `enabled = false` 即可。
