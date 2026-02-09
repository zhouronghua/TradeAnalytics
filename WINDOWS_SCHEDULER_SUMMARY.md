# Windows定时任务配置总结

## 快速开始（5步骤）

### 步骤1：打开任务计划程序
- 按 `Win+R`，输入：`taskschd.msc`

### 步骤2：创建基本任务
1. 点击右侧"创建基本任务"
2. 名称：`TradeAnalytics 股票分析`
3. 触发器：每天
4. 时间：`15:30`（收盘后30分钟）

### 步骤3：配置执行程序
- 程序：浏览选择 `run_analysis.bat`
- 起始位置：填写程序完整路径（如：`E:\code\TradeAnalytics`）

### 步骤4：高级设置
完成后，在弹出的属性对话框中：
- ✅ "不管用户是否登录都要运行"
- ✅ "使用最高权限运行"
- ✅ 取消勾选"只有在使用交流电源时才启动"

### 步骤5：测试运行
- 右键任务 → "运行"
- 检查微信是否收到推送

## 新功能

### 增强的推送内容

现在推送包含：

1. **今日摘要**
   - 符合条件的股票数量
   - 筛选条件说明

2. **近3日趋势**
   - 每天符合条件的股票数量
   - 趋势图标（📈增加 📉减少 ➡️持平）

3. **连续出现股票**
   - 连续两天都符合条件的股票
   - 这些是强势股，重点关注

4. **今日股票详情**
   - 每只股票的详细信息
   - 价格、均线、成交量倍数等

### 推送示例

```markdown
【股票分析结果 2026-02-09】

## 📊 今日摘要
- 分析日期: 2026-02-09
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
...详细信息...
```

## 配置说明

### config/config.ini

```ini
[Notification]
enabled = true
push_type = serverchan
serverchan_key = SCT你的Key

# 推送配置
push_history_days = 3  # 显示最近3天趋势
push_max_stocks = 20   # 每次最多推送20只股票
```

## 辅助脚本

### run_analysis.bat
- 用于任务计划程序执行
- 自动记录日志到 `logs/scheduler.log`

### start_background.bat  
- 后台常驻运行
- 适合不想配置任务计划程序的用户

### check_task.bat
- 检查任务状态
- 查看执行日志

## 常见问题

**Q: 如何验证任务是否正常？**
A: 双击 `check_task.bat` 查看状态和日志

**Q: 任务没有执行怎么办？**
A: 
1. 检查任务计划程序中任务状态
2. 查看 `logs/scheduler.log`
3. 手动运行 `run_analysis.bat` 测试

**Q: 如何修改执行时间？**
A: 任务计划程序 → 右键任务 → 属性 → 触发器 → 编辑

**Q: 想要开机自动启动怎么办？**
A: 
1. 按 `Win+R`，输入 `shell:startup`
2. 将 `start_background.bat` 快捷方式放入
3. 重启电脑测试

## 文件清单

新增文件：
- ✅ `run_analysis.bat` - 任务计划程序执行脚本
- ✅ `start_background.bat` - 后台常驻启动脚本
- ✅ `check_task.bat` - 任务检查脚本
- ✅ `WINDOWS_SCHEDULER_SETUP.md` - 详细配置文档（23页）
- ✅ `WINDOWS_SCHEDULER_SUMMARY.md` - 本文档（快速指南）

修改文件：
- ✅ `src/notification.py` - 增强推送功能，支持历史对比
- ✅ `config/config.ini` - 新增推送配置项

## 完整工作流程

```
开机/定时 15:30
    ↓
run_analysis.bat 启动
    ↓
执行 main.py
    ↓
1. 更新股票列表
2. 下载最新数据  
3. 分析筛选股票
4. 保存结果文件
    ↓
生成推送内容
- 读取今日结果
- 读取历史结果（近3天）
- 找出连续出现的股票
- 格式化为Markdown
    ↓
发送微信推送
    ↓
完成，等待下次执行
```

## 下一步

1. ✅ 配置微信推送（见 QUICKSTART_PUSH.md）
2. ✅ 配置Windows定时任务（见 WINDOWS_SCHEDULER_SETUP.md）
3. ✅ 运行 `check_task.bat` 验证配置
4. ✅ 等待明天15:30自动执行

## 技术支持

如遇问题：
1. 查看 `logs/scheduler.log`
2. 查看 `logs/task_scheduler.log`
3. 运行 `python test_push.py` 测试推送
4. 参考详细文档 `WINDOWS_SCHEDULER_SETUP.md`

---

**祝您投资顺利！📈**
