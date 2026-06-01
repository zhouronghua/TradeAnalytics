#!/usr/bin/env python
"""
首次运行初始化脚本
自动下载股票列表和历史数据
"""

import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_downloader import DataDownloader
from src.utils import Config


def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def main():
    """主程序"""
    print_section("TradeAnalytics 首次运行初始化")
    
    config_file = 'config/config.ini'
    
    # 检查配置文件
    if not os.path.exists(config_file):
        print(f"\n错误: 配置文件不存在: {config_file}")
        print("请先复制配置文件:")
        print(f"  cp config/config.ini.example {config_file}")
        print("\n然后编辑配置文件，至少配置以下项:")
        print("  [DataSource]")
        print("  source = baostock  # 或 akshare, tushare, tencent")
        return 1
    
    print(f"\n使用配置文件: {config_file}")
    
    try:
        config = Config(config_file)
        data_source = config.get('DataSource', 'source', fallback='baostock')
        print(f"数据源: {data_source}")
        
        # 初始化下载器
        print("\n正在初始化数据下载器...")
        downloader = DataDownloader(config_file)
        
        print_section("步骤1: 下载股票列表")
        print("\n正在下载股票列表...")
        stock_list = downloader.download_stock_list(force_update=True)
        
        if stock_list is None:
            print("\n错误: 股票列表下载失败")
            print("可能原因:")
            print("  1. 网络连接问题")
            print("  2. 数据源服务不可用")
            print("  3. 数据源配置错误")
            return 1
        
        print(f"\n成功获取 {len(stock_list)} 只股票")
        print(f"股票列表已保存到: {downloader.stocks_dir}/stock_list.csv")
        
        # 询问是否下载历史数据
        print_section("步骤2: 下载历史数据")
        print("\n注意:")
        print(f"  - 将下载 {len(stock_list)} 只股票的历史数据")
        print(f"  - 这可能需要较长时间（取决于网络速度和数据源）")
        print(f"  - 建议首次运行时在非交易时段进行")
        
        # 检查是否有下载限制
        limit_mb = config.getint('Download', 'daily_download_limit_mb', fallback=0)
        if limit_mb > 0:
            print(f"  - 当前下载限制: {limit_mb}MB")
            print(f"  - 建议首次运行时设置为 0（无限制）")
        
        print("\n是否继续下载历史数据? (y/n): ", end='')
        choice = input().strip().lower()
        
        if choice != 'y':
            print("\n已跳过历史数据下载")
            print("您可以稍后运行以下命令下载:")
            print(f"  python -c \"from src.data_downloader import DataDownloader; d=DataDownloader(); d.download_all_stocks()\"")
            print("\n或直接运行:")
            print("  python src/volume_analyzer.py")
            return 0
        
        # 下载历史数据
        print("\n开始下载历史数据...")
        print("提示: 按 Ctrl+C 可随时中断下载")
        
        success_count, fail_count = downloader.download_all_stocks(stock_list)
        total = success_count + fail_count
        
        print_section("下载完成")
        print(f"\n总计: {total} 只股票")
        print(f"成功: {success_count} 只")
        print(f"失败: {fail_count} 只")
        
        if success_count > 0:
            print(f"\n数据已保存到: {downloader.stocks_dir}")
            print("\n下一步:")
            print("  1. 运行测试: python test_batch_setup.py")
            print("  2. 运行分析: python src/volume_analyzer.py --no-update")
            print("  3. 添加定时任务: 参考 crontab_setup.md")
            return 0
        else:
            print("\n警告: 所有股票下载失败")
            print("请检查网络连接和数据源配置")
            return 1
        
    except KeyboardInterrupt:
        print("\n\n下载被用户中断")
        print("已下载的数据已保存，可稍后继续")
        return 130
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
