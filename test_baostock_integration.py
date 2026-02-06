"""
测试BaoStock集成
验证data_downloader.py是否正确使用BaoStock数据源
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data_downloader import DataDownloader
from src.utils import Config


def main():
    print("=" * 60)
    print("测试BaoStock集成")
    print("=" * 60)
    
    # 检查配置
    config = Config('config/config.ini')
    data_source = config.get('DataSource', 'source', fallback='akshare')
    
    print(f"\n1. 配置的数据源: {data_source}")
    
    if data_source.lower() != 'baostock':
        print("   [警告] 配置文件中数据源不是baostock")
        print("   请修改 config/config.ini 中的 [DataSource] source = baostock")
        return
    
    print("   [OK] 配置正确")
    
    # 初始化下载器
    print("\n2. 初始化DataDownloader...")
    try:
        downloader = DataDownloader('config/config.ini')
        print(f"   [OK] 使用数据源: {downloader.data_source}")
        
        if downloader.data_source != 'baostock':
            print(f"   [错误] 期望使用baostock但实际使用{downloader.data_source}")
            return
    except Exception as e:
        print(f"   [错误] {e}")
        return
    
    # 测试下载股票列表
    print("\n3. 测试下载股票列表...")
    try:
        stock_list = downloader.download_stock_list(force_update=True)
        if stock_list is not None:
            print(f"   [OK] 成功获取 {len(stock_list)} 只股票")
            print("\n   前5只股票:")
            print(stock_list.head().to_string(index=False))
        else:
            print("   [错误] 获取股票列表失败")
            return
    except Exception as e:
        print(f"   [错误] {e}")
        return
    
    # 测试下载单只股票
    print("\n4. 测试下载单只股票数据...")
    test_code = stock_list.iloc[0]['code']
    print(f"   测试股票: {test_code}")
    
    try:
        df = downloader.download_stock_history(test_code)
        if df is not None:
            print(f"   [OK] 成功获取 {len(df)} 天数据")
            print("\n   最近5天数据:")
            print(df.tail().to_string(index=False))
            
            # 检查数据完整性
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"   [警告] 缺少列: {missing_columns}")
            else:
                print("   [OK] 数据完整")
        else:
            print("   [错误] 获取股票数据失败")
            return
    except Exception as e:
        print(f"   [错误] {e}")
        return
    
    # 清理
    if downloader.baostock_source:
        downloader.baostock_source.logout()
    
    print("\n" + "=" * 60)
    print("测试完成 - BaoStock集成正常!")
    print("=" * 60)
    print("\n您现在可以运行:")
    print("  python main.py")


if __name__ == '__main__':
    main()
