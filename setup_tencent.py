#!/usr/bin/env python
"""
快速配置 Tencent 数据源脚本
自动优化配置文件以使用 Tencent 数据源和多线程下载
"""

import os
import sys
import configparser


def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def main():
    """主程序"""
    print_section("Tencent 数据源快速配置")
    
    config_file = 'config/config.ini'
    example_file = 'config/config.ini.example'
    
    # 检查配置文件
    if not os.path.exists(config_file):
        print(f"\n配置文件不存在，从示例文件创建...")
        if os.path.exists(example_file):
            import shutil
            shutil.copy(example_file, config_file)
            print(f"已创建配置文件: {config_file}")
        else:
            print(f"错误: 示例文件不存在: {example_file}")
            return 1
    
    # 读取配置
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    # 显示当前配置
    current_source = config.get('DataSource', 'source', fallback='未设置')
    current_workers = config.get('Download', 'max_workers', fallback='未设置')
    
    print(f"\n当前配置:")
    print(f"  数据源: {current_source}")
    print(f"  并发线程数: {current_workers}")
    
    # 询问用户
    print_section("配置选择")
    print("\n请选择配置方案:")
    print("  1. 首次下载（快速）- 10线程，无下载限制")
    print("  2. 日常使用（平衡）- 5线程，100MB限制")
    print("  3. 保守配置（稳定）- 3线程，增加重试")
    print("  4. 自定义配置")
    print("  0. 退出")
    
    choice = input("\n请输入选项 (0-4): ").strip()
    
    if choice == '0':
        print("已取消")
        return 0
    
    # 应用配置
    if choice == '1':
        # 首次下载配置
        config.set('DataSource', 'source', 'tencent')
        config.set('Download', 'max_workers', '10')
        config.set('Download', 'retry_times', '3')
        config.set('Download', 'retry_delay', '5')
        config.set('Download', 'daily_download_limit_mb', '0')
        
        print_section("已应用首次下载配置")
        print("  - 数据源: tencent")
        print("  - 并发线程数: 10")
        print("  - 下载限制: 无")
        print("  - 适合: 首次快速下载大量数据")
        
    elif choice == '2':
        # 日常使用配置
        config.set('DataSource', 'source', 'tencent')
        config.set('Download', 'max_workers', '5')
        config.set('Download', 'retry_times', '3')
        config.set('Download', 'retry_delay', '5')
        config.set('Download', 'daily_download_limit_mb', '100')
        
        print_section("已应用日常使用配置")
        print("  - 数据源: tencent")
        print("  - 并发线程数: 5")
        print("  - 下载限制: 100MB/天")
        print("  - 适合: 日常定时更新")
        
    elif choice == '3':
        # 保守配置
        config.set('DataSource', 'source', 'tencent')
        config.set('Download', 'max_workers', '3')
        config.set('Download', 'retry_times', '5')
        config.set('Download', 'retry_delay', '10')
        config.set('Download', 'daily_download_limit_mb', '100')
        
        print_section("已应用保守配置")
        print("  - 数据源: tencent")
        print("  - 并发线程数: 3")
        print("  - 重试次数: 5")
        print("  - 下载限制: 100MB/天")
        print("  - 适合: 网络不稳定环境")
        
    elif choice == '4':
        # 自定义配置
        print_section("自定义配置")
        
        print("\n数据源选择:")
        print("  1. tencent (速度快，支持多线程)")
        print("  2. baostock (稳定，数据完整)")
        print("  3. akshare (实时性好)")
        source_choice = input("请选择 (1-3): ").strip()
        
        if source_choice == '1':
            config.set('DataSource', 'source', 'tencent')
            workers = input("并发线程数 (建议5-10): ").strip() or '5'
        elif source_choice == '2':
            config.set('DataSource', 'source', 'baostock')
            workers = '1'
            print("BaoStock建议使用单线程")
        elif source_choice == '3':
            config.set('DataSource', 'source', 'akshare')
            workers = '1'
            print("AkShare建议使用单线程")
        else:
            print("无效选择，使用默认配置 tencent")
            config.set('DataSource', 'source', 'tencent')
            workers = '5'
        
        config.set('Download', 'max_workers', workers)
        
        limit = input("每日下载限制 MB (0=无限制): ").strip() or '0'
        config.set('Download', 'daily_download_limit_mb', limit)
        
        print_section("已应用自定义配置")
        print(f"  - 数据源: {config.get('DataSource', 'source')}")
        print(f"  - 并发线程数: {workers}")
        print(f"  - 下载限制: {limit}MB/天")
        
    else:
        print("无效选项")
        return 1
    
    # 保存配置
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)
    
    print(f"\n配置已保存到: {config_file}")
    
    # 下一步提示
    print_section("下一步操作")
    print("\n1. 查看完整配置:")
    print(f"   cat {config_file}")
    print("\n2. 开始首次下载:")
    print("   python init_first_run.py")
    print("\n3. 或直接运行分析:")
    print("   python src/volume_analyzer.py")
    print("\n4. 查看优化建议:")
    print("   cat TENCENT_DATASOURCE_OPTIMIZATION.md")
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(130)
