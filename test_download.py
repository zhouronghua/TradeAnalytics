"""
测试数据下载功能
只下载少量股票以验证功能
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data_downloader import DataDownloader
from src.data_analyzer import DataAnalyzer
from src.stock_filter import StockFilter

def test_download():
    """测试下载功能"""
    print("=" * 60)
    print("测试数据下载功能")
    print("=" * 60)
    
    # 初始化下载器
    downloader = DataDownloader()
    
    # 1. 下载股票列表
    print("\n[步骤1] 下载股票列表...")
    stock_list = downloader.download_stock_list(force_update=True)
    
    if stock_list is None or stock_list.empty:
        print("  获取股票列表失败")
        return False
    
    print(f"  成功获取 {len(stock_list)} 只股票")
    print(f"  前5只股票:")
    print(stock_list[['code', 'name', 'price']].head())
    
    # 2. 测试下载几只股票
    print("\n[步骤2] 测试下载股票数据（只下载前5只）...")
    test_stocks = stock_list.head(5)
    
    for idx, row in test_stocks.iterrows():
        stock_code = row['code']
        stock_name = row['name']
        
        print(f"\n  下载: {stock_code} {stock_name}")
        
        # 下载数据
        success = downloader.update_stock_data(stock_code)
        
        if success:
            print(f"    成功")
            
            # 读取并显示数据
            import pandas as pd
            file_path = os.path.join(downloader.daily_dir, f"{stock_code}.csv")
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                print(f"    数据行数: {len(df)}")
                print(f"    日期范围: {df['date'].min()} ~ {df['date'].max()}")
                print(f"    最新收盘价: {df['close'].iloc[-1]:.2f}")
        else:
            print(f"    失败")
    
    # 3. 显示下载统计
    print("\n[步骤3] 下载统计...")
    stats = downloader.get_download_stats()
    print(f"  已下载: {stats['downloaded_mb']:.2f}MB")
    print(f"  限制: {stats['limit_mb']:.0f}MB")
    print(f"  使用率: {stats['percentage']:.1f}%")
    print(f"  剩余: {stats['remaining_mb']:.2f}MB")
    
    return True


def test_analysis():
    """测试分析功能"""
    print("\n" + "=" * 60)
    print("测试数据分析功能")
    print("=" * 60)
    
    # 初始化分析器
    analyzer = DataAnalyzer(ma_period=120)
    
    # 读取本地数据进行分析
    daily_dir = 'data/daily'
    if not os.path.exists(daily_dir):
        print("  没有本地数据，请先运行下载测试")
        return False
    
    files = [f for f in os.listdir(daily_dir) if f.endswith('.csv')]
    if not files:
        print("  没有本地数据文件")
        return False
    
    print(f"\n  分析本地股票数据...")
    matched_count = 0
    
    for i, filename in enumerate(files[:5], 1):  # 只分析前5个
        stock_code = filename.replace('.csv', '')
        file_path = os.path.join(daily_dir, filename)
        
        print(f"\n  [{i}] 分析: {stock_code}")
        
        is_match, info = analyzer.analyze_from_file(
            file_path, 
            volume_ratio_threshold=5.0,
            ma_period=120
        )
        
        if is_match and info:
            matched_count += 1
            print(f"    ✓ 符合条件!")
            print(f"      价格: {info['close']:.2f}")
            print(f"      MA120: {info['ma']:.2f}")
            print(f"      成交量倍数: {info['volume_ratio']:.2f}")
        else:
            print(f"    × 不符合条件")
    
    print(f"\n  统计: {matched_count}/{min(5, len(files))} 只股票符合条件")
    
    return True


def main():
    """主测试函数"""
    try:
        # 测试下载
        success = test_download()
        
        if not success:
            print("\n下载测试失败")
            return 1
        
        # 测试分析
        test_analysis()
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print("\n提示:")
        print("1. 如需完整测试，运行: python main.py")
        print("2. 首次完整运行会下载大量数据（受100MB限制）")
        print("3. 可在 config/config.ini 中调整 daily_download_limit_mb")
        
        return 0
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
