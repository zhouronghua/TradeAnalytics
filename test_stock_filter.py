"""
测试股票过滤规则
验证是否正确过滤掉基金、债券等非股票证券
"""

from src.data_source_baostock_threadsafe import ThreadSafeBaoStockDataSource

def test_stock_filter():
    print("=" * 70)
    print("测试股票过滤规则")
    print("=" * 70)
    
    source = ThreadSafeBaoStockDataSource()
    
    print("\n获取股票列表...")
    stock_list = source.get_stock_list()
    
    if stock_list is None:
        print("获取失败！")
        return
    
    print(f"\n总共获取到 {len(stock_list)} 只股票\n")
    
    # 统计代码分布
    code_dist = {}
    for code in stock_list['code']:
        prefix = code[:2]
        code_dist[prefix] = code_dist.get(prefix, 0) + 1
    
    print("代码分布统计:")
    print("-" * 70)
    for prefix in sorted(code_dist.keys()):
        count = code_dist[prefix]
        description = ""
        if prefix == '60':
            description = "上交所主板"
        elif prefix == '68':
            description = "科创板"
        elif prefix == '00':
            description = "深交所主板"
        elif prefix == '30':
            description = "创业板"
        else:
            description = "其他"
        
        print(f"{prefix}xxxx: {count:4d} 只  ({description})")
    
    print("\n" + "-" * 70)
    
    # 检查是否有基金代码
    fund_codes = []
    for code in stock_list['code']:
        # 基金通常是 50xxxx, 51xxxx, 159xxx
        if code.startswith('50') or code.startswith('51') or code.startswith('159'):
            fund_codes.append(code)
    
    if fund_codes:
        print(f"\n警告：发现 {len(fund_codes)} 只可能的基金代码:")
        for code in fund_codes[:10]:  # 只显示前10个
            print(f"  {code}")
        if len(fund_codes) > 10:
            print(f"  ... 还有 {len(fund_codes) - 10} 只")
    else:
        print("\n通过：未发现基金代码")
    
    # 显示一些示例
    print("\n" + "=" * 70)
    print("股票列表示例（前20只）:")
    print("-" * 70)
    print(f"{'代码':<10} {'名称':<20}")
    print("-" * 70)
    for idx, row in stock_list.head(20).iterrows():
        print(f"{row['code']:<10} {row['name']:<20}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    
    # 清理
    source.cleanup()


if __name__ == '__main__':
    test_stock_filter()
