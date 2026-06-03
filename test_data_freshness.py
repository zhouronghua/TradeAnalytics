#!/usr/bin/env python
"""
数据时效性测试脚本
验证成交量分析只推送最近2天的数据
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.volume_analyzer import analyze_volume_surge


def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def create_test_data():
    """创建测试数据"""
    print_section("创建测试数据")
    
    test_dir = './test_data_freshness'
    os.makedirs(test_dir, exist_ok=True)
    
    today = datetime.now()
    
    # 创建不同日期的测试数据
    test_cases = [
        {
            'file': 'stock_today.csv',
            'date': today,
            'should_pass': True,
            'desc': '今天的数据（应该通过）'
        },
        {
            'file': 'stock_yesterday.csv',
            'date': today - timedelta(days=1),
            'should_pass': True,
            'desc': '昨天的数据（应该通过）'
        },
        {
            'file': 'stock_3days.csv',
            'date': today - timedelta(days=3),
            'should_pass': False,
            'desc': '3天前的数据（应该被过滤）'
        },
        {
            'file': 'stock_1month.csv',
            'date': today - timedelta(days=30),
            'should_pass': False,
            'desc': '1个月前的数据（应该被过滤）'
        },
        {
            'file': 'stock_3months.csv',
            'date': today - timedelta(days=90),
            'should_pass': False,
            'desc': '3个月前的数据（应该被过滤）'
        },
    ]
    
    print("\n创建测试文件:")
    
    for case in test_cases:
        # 创建测试数据
        dates = pd.date_range(
            end=case['date'],
            periods=30,
            freq='D'
        )
        
        data = {
            'date': dates.strftime('%Y-%m-%d'),
            'code': ['600000'] * len(dates),
            'open': [10.0] * len(dates),
            'high': [10.5] * len(dates),
            'low': [9.5] * len(dates),
            'close': [10.0] * len(dates),
            'volume': [1000000] * len(dates),
        }
        
        # 最后一天成交量暴涨（符合分析条件）
        data['volume'][-1] = 10000000  # 10倍
        data['close'][-1] = 10.5  # 价格上涨
        
        df = pd.DataFrame(data)
        file_path = os.path.join(test_dir, case['file'])
        df.to_csv(file_path, index=False)
        
        status = "✓ 应通过" if case['should_pass'] else "✗ 应被过滤"
        print(f"  {status} - {case['file']}: {case['desc']}")
        print(f"           最新日期: {case['date'].strftime('%Y-%m-%d')}")
    
    return test_dir, test_cases


def run_test(test_dir, test_cases):
    """运行测试"""
    print_section("运行时效性测试")
    
    # 获取测试文件
    import glob
    csv_files = glob.glob(os.path.join(test_dir, '*.csv'))
    
    print(f"\n测试文件数量: {len(csv_files)}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"时效性窗口: 最近2天")
    
    # 执行分析
    print("\n执行分析（max_days_old=2）...")
    results = analyze_volume_surge(
        csv_files,
        volume_avg_days=5,
        volume_ratio_threshold=5.0,
        ma_period=5,
        max_days_old=2  # 只保留最近2天
    )
    
    print(f"\n分析结果: 找到 {len(results)} 只符合条件的股票")
    
    return results


def verify_results(results, test_cases):
    """验证结果"""
    print_section("验证测试结果")
    
    today = datetime.now()
    cutoff_date = today - timedelta(days=2)
    
    print(f"\n时效性截止日期: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"预期通过的数据: 今天和昨天")
    print(f"预期被过滤: 3天前及更早")
    
    # 统计预期结果
    expected_pass = sum(1 for case in test_cases if case['should_pass'])
    expected_filter = sum(1 for case in test_cases if not case['should_pass'])
    
    print(f"\n预期通过: {expected_pass} 个")
    print(f"预期过滤: {expected_filter} 个")
    print(f"实际结果: {len(results)} 个")
    
    # 验证
    if len(results) == expected_pass:
        print("\n✓ 测试通过！时效性过滤工作正常")
        success = True
    else:
        print(f"\n✗ 测试失败！预期 {expected_pass} 个，实际 {len(results)} 个")
        success = False
    
    # 显示详细结果
    if not results.empty:
        print("\n通过的股票:")
        for _, row in results.iterrows():
            print(f"  - {row['stock_code']}: {row['date']}")
    
    # 显示应该被过滤的日期
    print("\n应该被过滤的日期:")
    for case in test_cases:
        if not case['should_pass']:
            print(f"  - {case['date'].strftime('%Y-%m-%d')}: {case['desc']}")
    
    return success


def cleanup(test_dir):
    """清理测试数据"""
    print_section("清理测试数据")
    
    try:
        import shutil
        shutil.rmtree(test_dir)
        print(f"\n已删除测试目录: {test_dir}")
    except Exception as e:
        print(f"\n清理失败: {e}")


def test_empty_notification():
    """测试空通知功能"""
    print_section("测试空通知功能")
    
    from src.notification import NotificationService
    
    try:
        notifier = NotificationService()
        
        if not notifier.enabled:
            print("\n消息推送未启用，跳过测试")
            print("如需测试，请在 config/config.ini 中启用 [Notification]")
            return True
        
        print(f"\n推送类型: {notifier.push_type}")
        print("正在发送测试空通知...")
        
        strategy_meta = {
            'ma_period': 20,
            'volume_ratio_threshold': 5.0,
            'from_validated': False
        }
        
        success = notifier.send_empty_analysis_result(
            datetime.now().strftime('%Y-%m-%d'),
            strategy_meta
        )
        
        if success:
            print("\n✓ 空通知发送成功！")
            print("请检查您的推送渠道是否收到消息")
            return True
        else:
            print("\n✗ 空通知发送失败")
            return False
            
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        return False


def main():
    """主程序"""
    print("="*60)
    print(" 数据时效性测试")
    print("="*60)
    print("\n本测试验证:")
    print("  1. 只保留最近2天的数据")
    print("  2. 过滤掉超过2天的旧数据")
    print("  3. 空通知功能正常工作")
    
    # 创建测试数据
    test_dir, test_cases = create_test_data()
    
    try:
        # 运行测试
        results = run_test(test_dir, test_cases)
        
        # 验证结果
        success = verify_results(results, test_cases)
        
        # 测试空通知
        print("\n" + "-"*60)
        input("\n按 Enter 继续测试空通知功能（或 Ctrl+C 跳过）...")
        test_empty_notification()
        
        return 0 if success else 1
        
    finally:
        # 清理
        print("\n" + "-"*60)
        choice = input("\n是否删除测试数据？(y/n): ").strip().lower()
        if choice == 'y':
            cleanup(test_dir)
        else:
            print(f"\n测试数据保留在: {test_dir}")


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(130)
