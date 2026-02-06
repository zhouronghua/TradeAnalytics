"""
根据当前实际数据进行分析
放宽条件：只要有足够的数据就分析
"""

import pandas as pd
import os
import glob

def analyze_stock_flexible(file_path):
    """灵活分析股票数据"""
    try:
        df = pd.read_csv(file_path, dtype={'code': str})
        
        if len(df) < 10:  # 至少需要10天数据
            return None, 0
        
        # 确保日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 计算能计算的均线
        if len(df) >= 120:
            ma_period = 120
        elif len(df) >= 60:
            ma_period = 60
        elif len(df) >= 30:
            ma_period = 30
        else:
            ma_period = 10
        
        df['ma'] = df['close'].rolling(window=ma_period).mean()
        
        # 获取最近的数据
        recent_data = df.tail(min(10, len(df)))
        
        results = []
        
        # 检查每一天
        for i in range(1, len(recent_data)):
            current = recent_data.iloc[i]
            previous = recent_data.iloc[i-1]
            
            # 跳过MA为空的数据
            if pd.isna(current['ma']):
                continue
            
            # 检查条件
            volume_ratio = current['volume'] / previous['volume'] if previous['volume'] > 0 else 0
            
            if volume_ratio >= 5.0 and current['close'] > current['ma']:
                stock_code = os.path.basename(file_path).replace('.csv', '')
                
                results.append({
                    'stock_code': stock_code,
                    'date': current['date'].strftime('%Y-%m-%d'),
                    'close': current['close'],
                    'ma': current['ma'],
                    'ma_period': ma_period,
                    'volume': current['volume'],
                    'prev_volume': previous['volume'],
                    'volume_ratio': volume_ratio,
                    'price_above_ma': ((current['close'] - current['ma']) / current['ma'] * 100)
                })
        
        return results, len(df)
    
    except Exception as e:
        return None, 0

def main():
    """主函数"""
    print("=" * 80)
    print("分析当前数据中的成交量暴涨股票")
    print("=" * 80)
    print("\n条件:")
    print("1. 成交量 >= 前一天的5倍")
    print("2. 收盘价 > 移动均线（根据数据长度自适应：120/60/30/10日）")
    print("3. 时间范围: 最近可用的交易日")
    print("-" * 80)
    
    # 获取所有CSV文件
    csv_files = glob.glob('data/daily/*.csv')
    
    print(f"\n找到 {len(csv_files)} 个数据文件")
    print("开始分析...\n")
    
    all_results = []
    processed = 0
    skipped = 0
    data_lengths = []
    
    for file_path in csv_files:
        results, data_len = analyze_stock_flexible(file_path)
        if data_len > 0:
            data_lengths.append(data_len)
        
        if results:
            all_results.extend(results)
            processed += 1
        else:
            skipped += 1
        
        # 显示进度
        if (processed + skipped) % 500 == 0:
            print(f"已处理: {processed + skipped}/{len(csv_files)}, 找到: {len(all_results)} 个符合条件")
    
    print(f"\n处理完成: 总计 {len(csv_files)} 个文件")
    print(f"找到符合条件: {len(all_results)} 个")
    
    if data_lengths:
        print(f"\n数据长度统计:")
        print(f"- 平均: {sum(data_lengths)/len(data_lengths):.0f} 天")
        print(f"- 最大: {max(data_lengths)} 天")
        print(f"- 最小: {min(data_lengths)} 天")
    
    print("-" * 80)
    
    if not all_results:
        print("\n未找到符合条件的股票")
        print("\n可能原因:")
        print("1. 数据还在下载中，数据量不足")
        print("2. 最近一周没有股票符合条件（成交量5倍 + 价格在均线上）")
        print("3. 数据时间范围不够")
        return
    
    # 转换为DataFrame并排序
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('volume_ratio', ascending=False)
    
    print(f"\n找到 {len(results_df)} 只符合条件的股票:")
    print("=" * 80)
    
    # 显示结果
    for idx, row in results_df.iterrows():
        print(f"\n股票代码: {row['stock_code']}")
        print(f"日期: {row['date']}")
        print(f"收盘价: {row['close']:.2f} 元")
        print(f"{row['ma_period']}日均线: {row['ma']:.2f} 元")
        print(f"高于均线: {row['price_above_ma']:.2f}%")
        print(f"当日成交量: {row['volume']:,.0f}")
        print(f"前日成交量: {row['prev_volume']:,.0f}")
        print(f"成交量倍数: {row['volume_ratio']:.2f} 倍")
        print("-" * 80)
    
    # 保存结果
    output_file = 'data/results/volume_surge_current.csv'
    os.makedirs('data/results', exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
