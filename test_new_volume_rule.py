"""
测试新的成交量规则
验证：当天成交量 >= 前7天平均成交量的5倍
"""

import pandas as pd
import os
from src.volume_analyzer import analyze_stock_flexible

def test_new_rule():
    print("=" * 70)
    print("测试新的成交量规则")
    print("规则：当天成交量 >= 前7天平均成交量的5倍，且收盘价 > 均线")
    print("=" * 70)
    
    # 找一些已有的股票数据进行测试
    data_dir = './data/daily'
    
    if not os.path.exists(data_dir):
        print("\n数据目录不存在，请先下载数据")
        return
    
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print("\n未找到数据文件，请先下载数据")
        return
    
    print(f"\n找到 {len(csv_files)} 个数据文件")
    print("随机测试前10个文件...\n")
    
    test_files = csv_files[:10]
    total_results = 0
    
    for csv_file in test_files:
        file_path = os.path.join(data_dir, csv_file)
        stock_code = csv_file.replace('.csv', '')
        
        results = analyze_stock_flexible(file_path)
        
        if results:
            print(f"\n股票 {stock_code} - 找到 {len(results)} 个符合条件的日期:")
            for result in results:
                print(f"  日期: {result['date']}")
                print(f"    收盘价: {result['close']:.2f}")
                print(f"    均线(MA{result['ma_period']}): {result['ma']:.2f}")
                print(f"    当天成交量: {result['volume']:,}")
                print(f"    前7日平均: {result['avg_7day_volume']:,}")
                print(f"    成交量倍数: {result['volume_ratio']:.2f}x")
                print(f"    价格高于均线: {result['price_above_ma']:.2f}%")
            total_results += len(results)
        else:
            print(f"股票 {stock_code} - 无符合条件的数据")
    
    print("\n" + "=" * 70)
    print(f"测试完成：在{len(test_files)}个文件中找到 {total_results} 个符合条件的记录")
    print("=" * 70)
    
    print("\n说明：")
    print("- 成交量倍数 = 当天成交量 / 前7天平均成交量")
    print("- 需要至少8个交易日的数据（当天 + 前7天）")
    print("- 价格需要高于均线（MA120/MA60/MA30/MA10，自适应）")


if __name__ == '__main__':
    test_new_rule()
