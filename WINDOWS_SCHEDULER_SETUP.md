# Windows 定时任务配置指南

## 概述

本指南将帮助您在Windows上配置定时任务，实现：
- 每个交易日（周一至周五）收盘后自动执行分析
- 自动推送当天成交量增长的股票详情
- 推送近几天的分析结果对比

## 方案选择

### 方案1：Windows任务计划程序（推荐）
- 系统自带，无需安装
- 开机自动运行
- 可视化界面配置
- **适合大多数用户**

### 方案2：保持程序常驻
- 程序一直运行，内置定时器
- 占用少量内存
- 需要手动启动或开机启动

## 方案1：Windows任务计划程序（详细步骤）

### 第一步：准备启动脚本

在程序目录创建 `run_analysis.bat` 文件：

```batch
@echo off
REM TradeAnalytics 自动分析脚本

REM 切换到程序目录
cd /d "%~dp0"

REM 记录启动时间
echo [%date% %time%] 开始执行股票分析... >> logs\scheduler.log

REM 执行分析程序
python main.py --auto-run

REM 记录完成时间
echo [%date% %time%] 分析完成 >> logs\scheduler.log
```

**保存为UTF-8编码**，避免中文乱码。

### 第二步：打开任务计划程序

1. 按 `Win+R` 键
2. 输入：`taskschd.msc`
3. 点击"确定"

或者：
- 在开始菜单搜索"任务计划程序"

### 第三步：创建基本任务

1. 在右侧"操作"面板，点击**"创建基本任务"**
2. 任务名称：`TradeAnalytics 股票分析`
3. 描述：`每个交易日15:30自动执行股票分析并推送结果`
4. 点击"下一步"

### 第四步：配置触发器

#### 4.1 选择触发器类型
- 选择：**"每天"**
- 点击"下一步"

#### 4.2 设置每日触发时间
- 开始时间：选择一个日期（如今天）
- 时间：**15:30**（收盘后30分钟）
- 重复执行间隔：**每 1 天**
- 点击"下一步"

### 第五步：配置操作

1. 选择：**"启动程序"**
2. 点击"下一步"
3. 配置程序：
   - **程序或脚本**：浏览选择 `run_analysis.bat`
   - **起始位置**：填写程序所在目录（如：`E:\code\TradeAnalytics`）
4. 点击"下一步"

### 第六步：高级设置

完成基本设置后，勾选"**当单击'完成'时，打开此任务属性的对话框**"，然后点击"完成"。

在属性对话框中：

#### 6.1 常规选项卡
- ✅ 勾选"不管用户是否登录都要运行"
- ✅ 勾选"使用最高权限运行"

#### 6.2 触发器选项卡
1. 双击现有触发器
2. 点击"新建"添加周末排除规则

**配置周一到周五运行**：
- 在"设置"部分，展开"高级设置"
- 勾选"启用"
- 在底部添加条件：
  - 点击"条件"选项卡
  - 自定义：添加PowerShell脚本检查是否为交易日

或者更简单的方法：
1. 保持每天触发
2. 让程序自己判断是否为交易日（程序已实现）

#### 6.3 条件选项卡
- ✅ 取消勾选"只有在计算机使用交流电源时才启动此任务"
  （这样笔记本电脑用电池也能运行）

#### 6.4 设置选项卡
- ✅ 勾选"如果任务失败，按下列方式重新启动"
  - 尝试重新启动次数：3 次
  - 间隔：10 分钟
- ✅ 勾选"如果任务运行时间超过以下时间，停止任务"
  - 设置为：2 小时（避免程序假死）

### 第七步：测试运行

1. 在任务计划程序中找到刚创建的任务
2. 右键点击，选择"**运行**"
3. 观察：
   - 命令窗口是否弹出
   - `logs/scheduler.log` 是否有记录
   - 微信是否收到推送

### 第八步：验证自动运行

**方法1：修改测试时间**
- 将触发时间改为几分钟后
- 等待自动运行

**方法2：查看历史记录**
- 在任务计划程序中，选择你的任务
- 查看"历史记录"选项卡
- 确认任务是否成功执行

## 方案2：程序常驻方式

### 创建开机启动脚本

创建 `start_background.bat`：

```batch
@echo off
REM 后台运行TradeAnalytics

cd /d "%~dp0"

REM 隐藏窗口运行
start /min "" python main.py

echo TradeAnalytics 已在后台启动
timeout /t 3
```

### 设置开机自启动

1. 按 `Win+R`，输入：`shell:startup`
2. 将 `start_background.bat` 的快捷方式放入该文件夹
3. 重启电脑测试

## 高级配置

### 只在交易日运行（PowerShell脚本）

创建 `check_trading_day.ps1`：

```powershell
# 检查是否为交易日
$today = Get-Date
$dayOfWeek = $today.DayOfWeek

# 周一到周五
if ($dayOfWeek -ge 1 -and $dayOfWeek -le 5) {
    # TODO: 这里可以添加节假日检查
    # 可以调用API或读取节假日配置文件
    exit 0  # 是交易日
} else {
    exit 1  # 不是交易日
}
```

在任务计划程序中添加条件：
1. 触发器 → 高级设置
2. 添加条件：`powershell -File check_trading_day.ps1`

### 推送近几天结果对比

程序已支持此功能（见下文增强功能）。

## 完整的配置文件示例

### config/config.ini

```ini
[Paths]
data_dir = ./data
daily_dir = ./data/daily
stocks_dir = ./data/stocks
results_dir = ./data/results
logs_dir = ./logs

[DataSource]
source = baostock
update_stock_list_days = 1

[Analysis]
ma_period = 120
volume_ratio_threshold = 5.0
min_history_days = 150

[Scheduler]
# 启用定时任务
enabled = true
# 每天15:30执行
run_time = 15:30
# 只在工作日执行（程序会自动判断）
weekdays_only = true

[Download]
max_workers = 1
retry_times = 3
retry_delay = 5
daily_download_limit_mb = 0

[Notification]
# 启用微信推送
enabled = true
push_type = serverchan
serverchan_key = SCT你的SendKey

# 推送配置
push_history_days = 3  # 推送最近3天的对比数据
push_max_stocks = 20   # 每次最多推送20只股票
```

## 推送内容增强

程序现在会推送：

1. **今日分析结果**
   - 符合条件的股票数量
   - 每只股票的详细信息

2. **近几天对比**（如果有历史数据）
   - 最近3天的股票数量趋势
   - 连续出现的股票（强势股）

推送示例：

```markdown
【股票分析结果 2026-02-09】

## 📊 今日摘要
- 符合条件股票: **8 只**
- 筛选条件: 成交量≥5倍 且 价格>均线

## 📈 近3日趋势
- 2026-02-09: 8 只
- 2026-02-08: 12 只
- 2026-02-07: 6 只

## ⭐ 今日股票列表

### 1. 603616 乐凯胶片 
- 收盘价: 8.29元
- 成交量倍数: 24.12
- 价格高于均线: 44.93%

...更多股票...
```

## 常见问题

### Q1: 任务计划程序中任务显示"正在运行"但没有反应？

**原因**：可能卡在某个步骤

**解决**：
1. 检查 `logs/` 目录下的日志
2. 在任务属性中设置超时时间（2小时）
3. 手动运行 `run_analysis.bat` 查看错误

### Q2: 任务历史记录显示"操作已完成(0x0)"但没有执行？

**原因**：路径配置错误

**解决**：
1. 确认"起始位置"填写正确
2. 使用完整的绝对路径
3. 检查Python是否在系统PATH中

### Q3: 如何查看任务执行日志？

**查看位置**：
1. `logs/scheduler.log` - 启动日志
2. `logs/task_scheduler.log` - 程序日志
3. 任务计划程序 → 历史记录选项卡

### Q4: 如何临时禁用自动执行？

**方法1**：修改 config.ini
```ini
[Scheduler]
enabled = false
```

**方法2**：在任务计划程序中
- 右键任务 → "禁用"

### Q5: 笔记本电脑合盖后还会执行吗？

**默认不会**。需要设置：
1. 控制面板 → 电源选项
2. 选择"合盖时不执行任何操作"
3. 或者改为"睡眠"，但任务计划程序需勾选"唤醒计算机以运行此任务"

### Q6: 如何修改执行时间？

1. 打开任务计划程序
2. 找到任务，右键 → 属性
3. 触发器选项卡 → 编辑
4. 修改时间为需要的时间（如15:00、16:00等）

### Q7: 如何在执行失败时收到通知？

可以在任务属性中配置：
- 操作选项卡 → 添加新操作
- 发送电子邮件（需要配置SMTP）

或者修改 `run_analysis.bat`：
```batch
python main.py --auto-run
if errorlevel 1 (
    REM 执行失败，发送通知
    python send_error_notification.py
)
```

## 最佳实践

### 1. 日志管理
- 定期清理旧日志（每月一次）
- 保留最近30天的日志即可

### 2. 数据备份
- 每周备份 `data/results/` 目录
- 使用Windows备份或云同步

### 3. 监控运行
- 第一周每天检查任务是否正常执行
- 确认微信推送正常接收
- 查看日志无异常

### 4. 性能优化
- 如果股票数据很多，考虑限制 `max_workers`
- 调整 `daily_download_limit_mb` 控制下载量

### 5. 安全建议
- 不要在 config.ini 中使用明文密码
- SendKey不要分享给他人
- 定期更换 SendKey

## 故障排除步骤

1. **检查Python环境**
   ```bash
   python --version
   python -c "import pandas, baostock, requests; print('OK')"
   ```

2. **手动运行脚本**
   ```bash
   run_analysis.bat
   ```

3. **查看日志**
   ```bash
   type logs\scheduler.log
   type logs\task_scheduler.log
   ```

4. **测试推送**
   ```bash
   python test_push.py
   ```

5. **检查任务状态**
   - 打开任务计划程序
   - 查看任务的"上次运行结果"
   - 查看"历史记录"选项卡

## 附录

### 完整的 run_analysis.bat

```batch
@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM ========================================
REM TradeAnalytics 自动分析脚本
REM ========================================

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 创建日志目录
if not exist logs mkdir logs

REM 记录开始时间
echo. >> logs\scheduler.log
echo ======================================== >> logs\scheduler.log
echo [%date% %time%] 任务开始 >> logs\scheduler.log
echo ======================================== >> logs\scheduler.log

REM 检查Python环境
python --version >> logs\scheduler.log 2>&1
if errorlevel 1 (
    echo [ERROR] Python未安装或不在PATH中 >> logs\scheduler.log
    goto :error
)

REM 执行分析
echo [%date% %time%] 开始执行分析... >> logs\scheduler.log
python main.py >> logs\scheduler.log 2>&1

REM 检查执行结果
if errorlevel 1 (
    echo [%date% %time%] 分析失败，错误码: %errorlevel% >> logs\scheduler.log
    goto :error
) else (
    echo [%date% %time%] 分析成功完成 >> logs\scheduler.log
    goto :success
)

:error
echo [%date% %time%] 任务执行失败 >> logs\scheduler.log
exit /b 1

:success
echo [%date% %time%] 任务执行成功 >> logs\scheduler.log
exit /b 0
```

### 检查脚本：check_task.bat

```batch
@echo off
echo 检查 TradeAnalytics 定时任务状态...
echo.

REM 检查任务是否存在
schtasks /query /tn "TradeAnalytics 股票分析" > nul 2>&1
if errorlevel 1 (
    echo [X] 任务不存在，请先创建
    goto :end
) else (
    echo [√] 任务已创建
)

REM 显示任务详情
schtasks /query /tn "TradeAnalytics 股票分析" /fo LIST /v

:end
pause
```

## 总结

通过以上配置，您的程序将：
1. ✅ 每天15:30自动运行（周一至周五）
2. ✅ 自动分析当天成交量增长的股票
3. ✅ 推送详细结果到微信
4. ✅ 包含近几天的对比数据
5. ✅ 完全无人值守

建议先手动测试几次，确认流程正常后再依赖自动执行。
