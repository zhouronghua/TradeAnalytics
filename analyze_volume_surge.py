"""
分析最近一周内成交量暴涨的股票
条件：
1. 某一天成交量是前一天的5倍以上
2. 收盘价高于120日均线
"""

import pandas as pd
import os
from datetime import datetime, timedelta
import glob

def calculate_ma(df, period=120):
    """计算移动平均线"""
    if len(df) < period:
        return None
    df['ma120'] = df['close'].rolling(window=period).mean()
    return df

def analyze_stock(file_path):
    """分析单只股票"""
    try:
        df = pd.read_csv(file_path, dtype={'code': str})
        
        if len(df) < 122:  # 需要至少122天数据（120天MA + 2天比较）
            return None
        
        # 确保日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 计算120日均线
        df = calculate_ma(df, 120)
        
        if df is None:
            return None
        
        # 获取最近一周的数据（最后7个交易日）
        recent_data = df.tail(8)  # 需要8天（7天+前一天做比较）
        
        results = []
        
        # 检查每一天
        for i in range(1, len(recent_data)):
            current = recent_data.iloc[i]
            previous = recent_data.iloc[i-1]
            
            # 跳过MA120为空的数据
            if pd.isna(current['ma120']):
                continue
            
            # 检查条件
            volume_ratio = current['volume'] / previous['volume'] if previous['volume'] > 0 else 0
            
            if volume_ratio >= 5.0 and current['close'] > current['ma120']:
                stock_code = os.path.basename(file_path).replace('.csv', '')
                
                results.append({
                    'stock_code': stock_code,
                    'date': current['date'].strftime('%Y-%m-%d'),
                    'close': current['close'],
                    'ma120': current['ma120'],
                    'volume': current['volume'],
                    'prev_volume': previous['volume'],
                    'volume_ratio': volume_ratio,
                    'price_above_ma': ((current['close'] - current['ma120']) / current['ma120'] * 100)
                })
        
        return results
    
    except Exception as e:
        return None

def main():
    """主函数"""
    print("=" * 80)
    print("分析最近一周成交量暴涨股票")
    print("=" * 80)
    print("\n条件:")
    print("1. 成交量 >= 前一天的5倍")
    print("2. 收盘价 > 120日均线")
    print("3. 时间范围: 最近一周")
    print("-" * 80)
    
    # 获取所有CSV文件
    csv_files = glob.glob('data/daily/*.csv')
    
    print(f"\n找到 {len(csv_files)} 个数据文件")
    print("开始分析...\n")
    
    all_results = []
    processed = 0
    skipped = 0
    
    for file_path in csv_files:
        results = analyze_stock(file_path)
        if results:
            all_results.extend(results)
            processed += 1
        else:
            skipped += 1
        
        # 显示进度
        if (processed + skipped) % 100 == 0:
            print(f"已处理: {processed + skipped}/{len(csv_files)}, 有效: {processed}, 跳过: {skipped}")
    
    print(f"\n处理完成: 总计 {len(csv_files)} 个文件")
    print(f"有效分析: {processed} 个")
    print(f"跳过: {skipped} 个（数据不足）")
    print("-" * 80)
    
    if not all_results:
        print("\n未找到符合条件的股票")
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
        print(f"120日均线: {row['ma120']:.2f} 元")
        print(f"高于均线: {row['price_above_ma']:.2f}%")
        print(f"当日成交量: {row['volume']:,.0f}")
        print(f"前日成交量: {row['prev_volume']:,.0f}")
        print(f"成交量倍数: {row['volume_ratio']:.2f} 倍")
        print("-" * 80)
    
    # 保存结果
    output_file = 'data/results/volume_surge_analysis.csv'
    os.makedirs('data/results', exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存到: {output_file}")
    
    # 统计
    print("\n统计信息:")
    print(f"- 平均成交量倍数: {results_df['volume_ratio'].mean():.2f} 倍")
    print(f"- 最高成交量倍数: {results_df['volume_ratio'].max():.2f} 倍")
    print(f"- 平均高于均线: {results_df['price_above_ma'].mean():.2f}%")
    print("\n按成交量倍数排名 TOP 10:")
    print(results_df.head(10)[['stock_code', 'date', 'volume_ratio', 'close', 'ma120']])

if __name__ == '__main__':
    main()
