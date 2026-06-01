#!/usr/bin/env python
"""
批处理配置测试脚本
测试 volume_analyzer.py 的各项功能是否正常
"""

import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import Config, setup_logger
from src.data_downloader import DataDownloader
from src.notification import NotificationService
from src.email_sender import EmailSender


def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def test_config_file(config_file='config/config.ini'):
    """测试配置文件"""
    print_section("1. 测试配置文件")
    
    if not os.path.exists(config_file):
        print(f"配置文件不存在: {config_file}")
        print("请复制 config/config.ini.example 并配置")
        return False
    
    try:
        config = Config(config_file)
        print(f"配置文件: {config_file}")
        print(f"数据目录: {config.get('Paths', 'data_dir', fallback='未配置')}")
        print(f"数据源: {config.get('DataSource', 'source', fallback='未配置')}")
        print(f"MA周期: {config.getint('Analysis', 'ma_period', fallback=0)}")
        print(f"量比阈值: {config.getfloat('Analysis', 'volume_ratio_threshold', fallback=0)}")
        print("配置文件读取正常")
        return True
    except Exception as e:
        print(f"配置文件读取失败: {e}")
        return False


def test_directories(config_file='config/config.ini'):
    """测试目录结构"""
    print_section("2. 测试目录结构")
    
    try:
        config = Config(config_file)
        
        dirs_to_check = [
            ('data_dir', config.get('Paths', 'data_dir', fallback='./data')),
            ('stocks_dir', config.get('Paths', 'stocks_dir', fallback='./data/stocks')),
            ('results_dir', config.get('Paths', 'results_dir', fallback='./data/results')),
            ('logs_dir', config.get('Paths', 'logs_dir', fallback='./logs')),
        ]
        
        all_ok = True
        for name, path in dirs_to_check:
            exists = os.path.exists(path)
            status = "存在" if exists else "不存在"
            print(f"{name}: {path} [{status}]")
            if not exists:
                all_ok = False
        
        if all_ok:
            print("所有目录正常")
        else:
            print("警告: 部分目录不存在，运行时会自动创建")
        
        return True
    except Exception as e:
        print(f"目录检查失败: {e}")
        return False


def test_data_source(config_file='config/config.ini'):
    """测试数据源"""
    print_section("3. 测试数据源")
    
    try:
        print("初始化数据下载器...")
        downloader = DataDownloader(config_file)
        print(f"数据源: {downloader.data_source}")
        print(f"最大并发数: {downloader.max_workers}")
        print(f"重试次数: {downloader.retry_times}")
        print("数据源配置正常")
        
        # 测试股票列表
        stock_list_file = os.path.join(
            downloader.stocks_dir, 
            'stock_list.csv'
        )
        if os.path.exists(stock_list_file):
            import pandas as pd
            df = pd.read_csv(stock_list_file)
            print(f"股票列表: {len(df)} 只股票")
        else:
            print("警告: 股票列表文件不存在，首次运行会自动下载")
        
        return True
    except Exception as e:
        print(f"数据源测试失败: {e}")
        return False


def test_email_config(config_file='config/config.ini'):
    """测试邮件配置"""
    print_section("4. 测试邮件配置")
    
    try:
        email_sender = EmailSender(config_file)
        
        print(f"邮件功能: {'启用' if email_sender.enabled else '禁用'}")
        
        if not email_sender.enabled:
            print("邮件功能未启用（在config.ini中设置 [Email] enabled=true 启用）")
            return True
        
        print(f"SMTP服务器: {email_sender.smtp_server}")
        print(f"SMTP端口: {email_sender.smtp_port}")
        print(f"发件人: {email_sender.sender_email}")
        print(f"收件人: {email_sender.receiver_emails}")
        
        if not email_sender.sender_email or not email_sender.auth_code:
            print("警告: 邮箱账号或授权码未配置")
            return False
        
        if not email_sender.receiver_emails:
            print("警告: 收件人未配置")
            return False
        
        print("\n发送测试邮件？(y/n): ", end='')
        choice = input().strip().lower()
        if choice == 'y':
            print("正在发送测试邮件...")
            if email_sender.send_test():
                print("测试邮件发送成功!")
            else:
                print("测试邮件发送失败")
                return False
        
        return True
        
    except Exception as e:
        print(f"邮件配置测试失败: {e}")
        return False


def test_notification_config(config_file='config/config.ini'):
    """测试方糖推送配置"""
    print_section("5. 测试方糖推送配置")
    
    try:
        notifier = NotificationService(config_file)
        
        print(f"推送功能: {'启用' if notifier.enabled else '禁用'}")
        
        if not notifier.enabled:
            print("推送功能未启用（在config.ini中设置 [Notification] enabled=true 启用）")
            return True
        
        print(f"推送类型: {notifier.push_type}")
        
        if notifier.push_type == 'serverchan':
            if notifier.serverchan_key:
                print(f"Server酱Key: {notifier.serverchan_key[:8]}...")
            else:
                print("警告: Server酱SendKey未配置")
                return False
        elif notifier.push_type == 'qywechat':
            if notifier.qywechat_webhook:
                print(f"企业微信Webhook: 已配置")
            else:
                print("警告: 企业微信Webhook未配置")
                return False
        elif notifier.push_type == 'pushplus':
            if notifier.pushplus_token:
                print(f"PushPlus Token: 已配置")
            else:
                print("警告: PushPlus Token未配置")
                return False
        
        print("\n发送测试推送？(y/n): ", end='')
        choice = input().strip().lower()
        if choice == 'y':
            print("正在发送测试推送...")
            if notifier.send_test_message():
                print("测试推送发送成功!")
            else:
                print("测试推送发送失败")
                return False
        
        return True
        
    except Exception as e:
        print(f"推送配置测试失败: {e}")
        return False


def test_volume_analyzer(config_file='config/config.ini'):
    """测试成交量分析器"""
    print_section("6. 测试成交量分析器")
    
    try:
        from src.volume_analyzer import VolumeAnalyzer
        
        print("初始化成交量分析器...")
        analyzer = VolumeAnalyzer(config_file)
        
        print(f"MA周期: {analyzer.ma_period}")
        print(f"量比阈值: {analyzer.volume_ratio}")
        print(f"数据目录: {analyzer.daily_dir}")
        print(f"结果目录: {analyzer.results_dir}")
        
        # 检查数据文件
        import glob
        csv_files = glob.glob(os.path.join(analyzer.daily_dir, '*.csv'))
        
        if csv_files:
            print(f"数据文件: {len(csv_files)} 个")
            print("成交量分析器配置正常")
        else:
            print("警告: 未找到股票数据文件")
            print("请先运行数据下载: python src/data_downloader.py")
        
        return True
        
    except Exception as e:
        print(f"成交量分析器测试失败: {e}")
        return False


def main():
    """主程序"""
    print("="*60)
    print(" Volume Analyzer 批处理配置测试")
    print("="*60)
    print("\n此脚本将测试批处理所需的各项配置")
    
    config_file = 'config/config.ini'
    
    # 运行测试
    tests = [
        ('配置文件', lambda: test_config_file(config_file)),
        ('目录结构', lambda: test_directories(config_file)),
        ('数据源', lambda: test_data_source(config_file)),
        ('邮件配置', lambda: test_email_config(config_file)),
        ('方糖推送', lambda: test_notification_config(config_file)),
        ('成交量分析器', lambda: test_volume_analyzer(config_file)),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except KeyboardInterrupt:
            print("\n\n测试被用户中断")
            return 1
        except Exception as e:
            print(f"\n测试异常: {e}")
            results.append((name, False))
    
    # 总结
    print_section("测试总结")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}  {name}")
    
    print(f"\n总计: {passed}/{total} 项通过")
    
    if passed == total:
        print("\n所有测试通过! 可以添加到 crontab 运行了")
        print("\n添加到 crontab 的示例命令:")
        print(f"30 15 * * 1-5 cd {os.getcwd()} && python src/volume_analyzer.py")
        return 0
    else:
        print("\n部分测试未通过，请检查配置后再添加到 crontab")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(130)
