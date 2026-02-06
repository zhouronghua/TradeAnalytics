"""
直接测试BaoStock数据源切换
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.data_downloader import DataDownloader

def test_data_source():
    """测试数据源"""
    print("=" * 60)
    print("测试数据源配置")
    print("=" * 60)
    
    downloader = DataDownloader('config/config.ini')
    
    print(f"\n当前数据源: {downloader.data_source}")
    print(f"BaoStock可用: {downloader.baostock_source is not None}")
    
    if downloader.data_source == 'baostock':
        print("\n[OK] 已配置使用BaoStock数据源")
    else:
        print(f"\n[WARNING] 当前使用 {downloader.data_source} 数据源")
    
    print("\n" + "=" * 60)
    print("测试下载股票列表")
    print("=" * 60)
    
    stock_list = downloader.download_stock_list(force_update=True)
    
    if stock_list is not None:
        print(f"\n[OK] 成功获取股票列表: {len(stock_list)} 只")
        print("\n前5只股票:")
        print(stock_list.head())
        
        # 测试下载单只股票
        test_code = stock_list.iloc[0]['code']
        print(f"\n" + "=" * 60)
        print(f"测试下载股票 {test_code} 数据")
        print("=" * 60)
        
        df = downloader.download_stock_history(test_code)
        if df is not None:
            print(f"\n[OK] 成功下载 {test_code} 数据: {len(df)} 天")
            print("\n最近5天数据:")
            print(df.tail())
        else:
            print(f"\n[FAIL] 下载 {test_code} 失败")
    else:
        print("\n[FAIL] 获取股票列表失败")
    
    # 清理
    if downloader.baostock_source:
        downloader.baostock_source.logout()

if __name__ == '__main__':
    test_data_source()
