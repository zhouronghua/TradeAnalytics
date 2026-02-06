"""
测试下载量限制功能
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data_downloader import DataDownloader

def test_download_limit():
    """测试下载限制"""
    print("=" * 60)
    print("测试下载量限制功能")
    print("=" * 60)
    
    # 创建下载器（使用100MB限制）
    downloader = DataDownloader()
    
    # 手动设置限制为100MB进行测试
    downloader.daily_download_limit_mb = 100
    downloader.download_limit_bytes = 100 * 1024 * 1024
    downloader.downloaded_bytes = 0
    
    print(f"\n配置的下载限制: {downloader.daily_download_limit_mb}MB")
    print(f"限制字节数: {downloader.download_limit_bytes:,} bytes\n")
    
    # 模拟下载不同大小的数据
    test_cases = [
        ("首次下载5只股票", 5, 150),   # 5只 × 150天
        ("日常更新5只股票", 5, 1),     # 5只 × 1天
        ("首次下载100只股票", 100, 150), # 100只 × 150天
        ("首次下载1000只股票", 1000, 150), # 1000只 × 150天
        ("首次下载5000只股票", 5000, 150), # 5000只 × 150天（全部）
    ]
    
    for desc, stock_count, days in test_cases:
        # 重置计数器
        downloader.downloaded_bytes = 0
        
        # 模拟下载
        for i in range(stock_count):
            # 每只股票days天的数据
            estimated_size = days * 100  # 每行约100字节
            downloader.downloaded_bytes += estimated_size
            
            # 检查是否超限
            if not downloader.check_download_limit():
                print(f"\n{desc}:")
                stats = downloader.get_download_stats()
                print(f"  模拟下载了 {i} 只股票后达到限制")
                print(f"  已下载: {stats['downloaded_mb']:.2f}MB / {stats['limit_mb']:.0f}MB")
                print(f"  使用率: {stats['percentage']:.1f}%")
                break
        else:
            # 全部下载完成
            stats = downloader.get_download_stats()
            print(f"\n{desc}:")
            print(f"  成功下载 {stock_count} 只股票")
            print(f"  已下载: {stats['downloaded_mb']:.2f}MB / {stats['limit_mb']:.0f}MB")
            print(f"  使用率: {stats['percentage']:.1f}%")
    
    # 测试无限制模式
    print("\n" + "=" * 60)
    print("测试无限制模式")
    print("=" * 60)
    
    downloader.daily_download_limit_mb = 0
    downloader.downloaded_bytes = 0
    
    print("\n设置为无限制 (daily_download_limit_mb = 0)")
    
    # 模拟下载大量数据
    for i in range(10000):
        estimated_size = 150 * 100
        downloader.downloaded_bytes += estimated_size
    
    stats = downloader.get_download_stats()
    print(f"模拟下载 10000 只股票")
    print(f"已下载: {stats['downloaded_mb']:.2f}MB")
    print(f"继续下载: {'是' if downloader.check_download_limit() else '否'}")


if __name__ == '__main__':
    test_download_limit()
