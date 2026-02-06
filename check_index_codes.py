"""
检查000001-000020这些代码是否是指数
"""

from src.data_source_baostock_threadsafe import ThreadSafeBaoStockDataSource
from datetime import datetime, timedelta

def check_codes():
    print("检查特殊代码...")
    
    source = ThreadSafeBaoStockDataSource()
    
    # 检查这些可疑的代码
    test_codes = ['000001', '000002', '000004', '000005', '000010', '000016']
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    for code in test_codes:
        print(f"\n检查 {code}:")
        df = source.get_stock_history(code, start_date, end_date)
        if df is not None and len(df) > 0:
            print(f"  有数据：{len(df)} 天")
            print(f"  最新日期：{df.iloc[-1]['date']}")
            print(f"  最新收盘价：{df.iloc[-1]['close']}")
        else:
            print(f"  无数据")
    
    source.cleanup()


if __name__ == '__main__':
    check_codes()
