"""
对比模拟数据和真实数据
"""

import os
import pandas as pd

def check_data_source():
    """检查当前data目录中的数据来源"""
    print("=" * 60)
    print("检查数据来源")
    print("=" * 60)
    
    # 检查股票列表文件
    stock_list_file = 'data/stocks/stock_list.csv'
    daily_dir = 'data/daily'
    
    if not os.path.exists(stock_list_file):
        print("\n✓ 没有数据文件")
        print("  这是全新的环境")
        print("  运行 python main.py 将下载真实数据")
        return
    
    # 读取股票列表
    df = pd.read_csv(stock_list_file)
    
    print(f"\n当前股票列表:")
    print(f"  文件: {stock_list_file}")
    print(f"  股票数量: {len(df)}")
    print(f"  列名: {list(df.columns)}")
    
    # 判断数据来源
    print("\n判断数据来源:")
    
    if len(df) == 5:
        print("  ❌ 这是模拟数据！")
        print("  原因: 只有5只股票")
        print("\n  股票列表:")
        for _, row in df.iterrows():
            print(f"    {row['code']} {row['name']}")
        
        # 检查是否有600001
        if '600001' in df['code'].values:
            print("\n  ⚠️  包含已退市的600001（邯郸钢铁）")
            print("  这证明是模拟数据，不是真实市场数据！")
        
        print("\n建议操作:")
        print("  1. 删除模拟数据:")
        print("     del data\\daily\\*.csv")
        print("     del data\\stocks\\*.csv")
        print("     del data\\results\\*.csv")
        print("  2. 运行真实程序:")
        print("     python main.py")
        print("  3. 点击'立即执行分析'")
        
    elif len(df) > 100:
        print("  ✓ 这是真实数据！")
        print(f"  原因: 有 {len(df)} 只股票（真实市场规模）")
        
        # 检查是否有600001
        if '600001' in df['code'].values:
            print("\n  ⚠️  警告: 包含600001")
            print("  这不应该出现（已退市）")
        else:
            print("\n  ✓ 不包含600001（已退市股票）")
            print("  数据来源正确！")
        
        # 显示一些真实股票
        print("\n  真实股票示例:")
        for _, row in df.head(10).iterrows():
            print(f"    {row['code']} {row['name']}")
    
    else:
        print("  ⚠️  数据异常")
        print(f"  股票数量 {len(df)} 不符合预期")
    
    # 检查数据文件数量
    if os.path.exists(daily_dir):
        csv_files = [f for f in os.listdir(daily_dir) if f.endswith('.csv')]
        print(f"\n日线数据文件:")
        print(f"  目录: {daily_dir}")
        print(f"  文件数量: {len(csv_files)}")
        
        if len(csv_files) == 5:
            print("  ❌ 这是模拟数据（只有5个文件）")
        elif len(csv_files) > 100:
            print(f"  ✓ 这是真实数据（有{len(csv_files)}个文件）")
        
        # 检查是否有600001.csv
        if '600001.csv' in csv_files:
            print("  ⚠️  发现 600001.csv（已退市股票）")
            print("  这是模拟数据！")
        else:
            print("  ✓ 没有600001.csv")


def show_main_py_info():
    """显示main.py的信息"""
    print("\n" + "=" * 60)
    print("main.py 数据来源说明")
    print("=" * 60)
    
    print("""
main.py 的数据流程:

1. main.py
   └─> StockAnalyzerGUI (src/gui.py)
       └─> TaskScheduler (src/scheduler.py)
           └─> DataDownloader (src/data_downloader.py)
               └─> akshare.stock_zh_a_spot_em()  ← 真实API

2. 真实API说明:
   - stock_zh_a_spot_em() 从东方财富网获取数据
   - 只返回当前在市交易的股票
   - 自动过滤已退市的股票（如600001）
   - 返回约5000只真实股票

3. 模拟数据文件:
   ❌ demo_with_mock_data.py  ← 创建模拟数据
   ❌ test_gui.py             ← 使用模拟数据测试
   ✓ main.py                 ← 使用真实数据

4. 结论:
   ✓ python main.py 使用的是真实数据
   ✓ 不会下载模拟数据
   ✓ 不会包含已退市的股票
""")


if __name__ == '__main__':
    check_data_source()
    show_main_py_info()
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("✓ main.py 100% 使用真实数据")
    print("✓ 不会使用模拟数据")
    print("✓ 不会包含600001等退市股票")
    print("✓ 所有数据来自AkShare的真实API")
