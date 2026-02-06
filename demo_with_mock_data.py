"""
使用模拟数据演示功能
不需要网络连接
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils import ensure_dir, safe_write_csv
from src.data_analyzer import DataAnalyzer
from src.stock_filter import StockFilter


def create_mock_data():
    """创建模拟数据"""
    print("=" * 60)
    print("创建模拟股票数据")
    print("=" * 60)
    
    ensure_dir('data/daily')
    ensure_dir('data/stocks')
    ensure_dir('data/results')
    
    # 创建股票列表
    stock_list = pd.DataFrame({
        'code': ['000001', '000002', '000003', '600000', '600001'],
        'name': ['平安银行', '万科A', '国农科技', '浦发银行', '邯郸钢铁'],
        'price': [15.20, 12.50, 18.80, 10.30, 5.60],
        'market': ['SZ', 'SZ', 'SZ', 'SH', 'SH']
    })
    
    # 确保code列是字符串类型
    stock_list['code'] = stock_list['code'].astype(str)
    
    safe_write_csv(stock_list, 'data/stocks/stock_list.csv')
    print(f"\n已创建股票列表: {len(stock_list)} 只股票")
    print(stock_list)
    
    # 为每只股票创建150天的历史数据
    print("\n创建历史交易数据...")
    
    for idx, row in stock_list.iterrows():
        stock_code = row['code']
        stock_name = row['name']
        base_price = row['price']
        
        # 生成150天的数据
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') 
                for i in range(150, 0, -1)]
        
        # 生成价格数据（带随机波动）
        np.random.seed(int(stock_code))
        price_changes = np.random.normal(0, 0.02, 150)
        prices = base_price * (1 + price_changes).cumprod()
        
        # 生成成交量（随机）
        volumes = np.random.uniform(1000000, 5000000, 150)
        
        # 关键：让最后一天的成交量是前一天的6倍（符合筛选条件）
        if idx % 2 == 0:  # 一半的股票符合条件
            volumes[-1] = volumes[-2] * 6.5
            prices[-1] = prices[-20:].mean() * 1.05  # 确保在均线上方
        
        # 创建DataFrame
        df = pd.DataFrame({
            'date': dates,
            'open': prices * 0.99,
            'close': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'volume': volumes.astype(int),
            'amount': (volumes * prices).astype(int)
        })
        
        # 保存
        file_path = f'data/daily/{stock_code}.csv'
        safe_write_csv(df, file_path)
        
        print(f"  {stock_code} {stock_name}: {len(df)}天数据, 价格范围 {df['close'].min():.2f}-{df['close'].max():.2f}")
    
    print("\n模拟数据创建完成！")
    return stock_list


def test_analyzer():
    """测试分析功能"""
    print("\n" + "=" * 60)
    print("测试数据分析功能")
    print("=" * 60)
    
    analyzer = DataAnalyzer(ma_period=120)
    
    daily_dir = 'data/daily'
    files = sorted([f for f in os.listdir(daily_dir) if f.endswith('.csv')])
    
    print(f"\n找到 {len(files)} 个数据文件")
    
    for filename in files:
        stock_code = filename.replace('.csv', '')
        file_path = os.path.join(daily_dir, filename)
        
        print(f"\n分析: {stock_code}")
        
        # 读取数据
        df = pd.read_csv(file_path)
        print(f"  数据: {len(df)}天, {df['date'].min()} ~ {df['date'].max()}")
        print(f"  最新价格: {df['close'].iloc[-1]:.2f}")
        print(f"  最新成交量: {df['volume'].iloc[-1]:,}")
        print(f"  前日成交量: {df['volume'].iloc[-2]:,}")
        print(f"  成交量倍数: {df['volume'].iloc[-1] / df['volume'].iloc[-2]:.2f}")
        
        # 分析
        is_match, info = analyzer.analyze_from_file(
            file_path, 
            volume_ratio_threshold=5.0,
            ma_period=120
        )
        
        if is_match and info:
            print(f"  [OK] 符合筛选条件!")
            print(f"    收盘价: {info['close']:.2f}")
            print(f"    MA120: {info['ma']:.2f}")
            print(f"    成交量倍数: {info['volume_ratio']:.2f}")
        else:
            print(f"  [NO] 不符合条件")


def test_filter():
    """测试筛选功能"""
    print("\n" + "=" * 60)
    print("测试股票筛选功能")
    print("=" * 60)
    
    stock_filter = StockFilter()
    
    # 读取股票列表
    stock_list = pd.read_csv('data/stocks/stock_list.csv')
    
    def progress_callback(current, total, stock_code, matched):
        print(f"  进度: {current}/{total} - {stock_code} {'[匹配]' if matched else ''}")
    
    # 执行筛选
    print("\n执行筛选...")
    matched_stocks, output_file = stock_filter.run_filter(callback=progress_callback)
    
    print(f"\n筛选完成！")
    print(f"符合条件: {len(matched_stocks)} 只股票")
    
    if matched_stocks:
        print("\n符合条件的股票:")
        print("-" * 60)
        for i, stock in enumerate(matched_stocks, 1):
            print(f"{i}. {stock['code']} {stock['name']}")
            print(f"   价格: {stock['close']:.2f}  MA120: {stock['ma']:.2f}")
            print(f"   成交量倍数: {stock['volume_ratio']:.2f}倍")
            print()
    
    if output_file:
        print(f"结果已保存到: {output_file}")
        
        # 读取并显示结果文件
        result_df = pd.read_csv(output_file)
        print("\n结果文件内容:")
        print(result_df.to_string())


def test_download_limit():
    """测试下载限制功能"""
    print("\n" + "=" * 60)
    print("测试下载限制功能")
    print("=" * 60)
    
    from src.data_downloader import DataDownloader
    
    downloader = DataDownloader()
    
    print(f"\n配置的下载限制: {downloader.daily_download_limit_mb}MB")
    
    # 模拟下载一些数据
    print("\n模拟下载数据...")
    
    # 模拟下载5个文件，每个约20MB
    for i in range(5):
        # 模拟数据大小（20MB）
        simulated_size = 20 * 1024 * 1024
        downloader.downloaded_bytes += simulated_size
        
        stats = downloader.get_download_stats()
        can_continue = downloader.check_download_limit()
        
        print(f"\n第{i+1}次下载:")
        print(f"  已下载: {stats['downloaded_mb']:.2f}MB / {stats['limit_mb']:.0f}MB")
        print(f"  使用率: {stats['percentage']:.1f}%")
        print(f"  剩余: {stats['remaining_mb']:.2f}MB")
        print(f"  可以继续: {'是' if can_continue else '否[已达限制]'}")
        
        if not can_continue:
            print("\n已达到下载限制，停止下载")
            break


def main():
    """主函数"""
    try:
        print("\n" + "=" * 60)
        print("股票分析软件功能演示（使用模拟数据）")
        print("=" * 60)
        
        # 1. 创建模拟数据
        create_mock_data()
        
        # 2. 测试分析功能
        test_analyzer()
        
        # 3. 测试筛选功能
        test_filter()
        
        # 4. 测试下载限制
        test_download_limit()
        
        print("\n" + "=" * 60)
        print("功能演示完成！")
        print("=" * 60)
        
        print("\n说明:")
        print("1. 已成功创建模拟数据并演示了所有核心功能")
        print("2. 增量下载机制已实现（检查本地最新日期）")
        print("3. 下载量限制已实现（默认100MB/天）")
        print("4. 筛选条件：成交量5倍+价格在MA120上")
        print("\n实际使用:")
        print("- 运行 python main.py 启动GUI")
        print("- 首次运行会从网络下载真实数据")
        print("- 第二天起只下载增量数据")
        print("- 下载量受100MB限制保护")
        
        return 0
        
    except Exception as e:
        print(f"\n演示失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
