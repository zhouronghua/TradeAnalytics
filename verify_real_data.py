"""
验证真实股票数据
检查600001是否还在交易
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_stock_600001():
    """检查600001邯郸钢铁是否还在交易"""
    print("=" * 60)
    print("验证：600001邯郸钢铁是否还在A股市场")
    print("=" * 60)
    
    try:
        import akshare as ak
        
        print("\n1. 从AkShare获取当前A股列表...")
        stock_list = ak.stock_zh_a_spot_em()
        
        print(f"   获取到 {len(stock_list)} 只股票")
        print(f"   列名: {list(stock_list.columns)}")
        
        # 检查600001是否在列表中
        print("\n2. 检查600001是否在列表中...")
        code_600001 = stock_list[stock_list['代码'] == '600001']
        
        if code_600001.empty:
            print("   ❌ 600001不在当前A股列表中")
            print("   原因: 该股票已于2009年退市")
            print("   说明: AkShare只返回当前在市股票")
        else:
            print("   ✓ 600001在列表中")
            print(f"   名称: {code_600001['名称'].values[0]}")
            print(f"   最新价: {code_600001['最新价'].values[0]}")
        
        # 显示一些真实的上交所股票
        print("\n3. 显示真实的上交所600xxx股票示例:")
        sh_stocks = stock_list[stock_list['代码'].str.startswith('600')].head(10)
        for _, row in sh_stocks.iterrows():
            print(f"   {row['代码']} {row['名称']} - {row['最新价']:.2f}元")
        
        # 检查本地模拟数据
        print("\n4. 检查本地数据目录:")
        if os.path.exists('data/daily/600001.csv'):
            print("   ⚠️  发现 data/daily/600001.csv")
            print("   这是模拟数据文件!")
            print("   建议删除模拟数据，运行真实下载")
        else:
            print("   ✓ 没有600001的数据文件")
        
        # 说明
        print("\n" + "=" * 60)
        print("结论:")
        print("=" * 60)
        print("1. AkShare不会返回已退市的股票")
        print("2. 您看到的600001数据是演示脚本创建的模拟数据")
        print("3. 真实使用时，只会下载当前在市的股票")
        print("\n建议操作:")
        print("1. 删除模拟数据: 删除 data/ 目录下的所有.csv文件")
        print("2. 运行真实下载: python main.py -> 点击'立即执行分析'")
        print("3. 等待完成: 首次下载需要30-60分钟")
        print("4. 查看结果: 都是真实在市股票的数据")
        
    except ImportError:
        print("\n❌ AkShare未安装")
        print("   请运行: pip install akshare")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def clean_mock_data():
    """清理模拟数据"""
    print("\n" + "=" * 60)
    print("清理模拟数据")
    print("=" * 60)
    
    import shutil
    
    dirs_to_clean = [
        'data/daily',
        'data/stocks', 
        'data/results'
    ]
    
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            files = [f for f in os.listdir(dir_path) if f.endswith('.csv')]
            if files:
                print(f"\n{dir_path} 中有 {len(files)} 个文件")
                
                choice = input(f"是否删除这些文件? (y/n): ").lower()
                if choice == 'y':
                    for f in files:
                        file_path = os.path.join(dir_path, f)
                        os.remove(file_path)
                        print(f"  已删除: {f}")
                    print(f"✓ 已清理 {dir_path}")
                else:
                    print(f"跳过 {dir_path}")
    
    print("\n模拟数据清理完成！")
    print("现在可以运行 python main.py 下载真实数据")


if __name__ == '__main__':
    check_stock_600001()
    
    print("\n")
    choice = input("是否清理模拟数据? (y/n): ").lower()
    if choice == 'y':
        clean_mock_data()
