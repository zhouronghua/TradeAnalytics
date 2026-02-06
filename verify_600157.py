"""
验证600157的价格数据
"""

import pandas as pd
import baostock as bs
import os

def verify_600157():
    """验证600157数据"""
    stock_code = "600157"
    csv_file = f"data/daily/{stock_code}.csv"
    
    print("=" * 70)
    print(f"验证 {stock_code} 数据")
    print("=" * 70)
    
    # 1. 检查本地文件
    print("\n[1] 本地CSV文件数据")
    print("-" * 70)
    
    if os.path.exists(csv_file):
        df_local = pd.read_csv(csv_file)
        print(f"文件: {csv_file}")
        print(f"行数: {len(df_local)}")
        print(f"修改时间: {pd.to_datetime(os.path.getmtime(csv_file), unit='s')}")
        print("\n最后5天数据:")
        print(df_local.tail())
        
        if len(df_local) > 0:
            last_date = df_local.iloc[-1]['date']
            last_close = df_local.iloc[-1]['close']
            print(f"\n本地最新: {last_date}, 收盘价: {last_close:.2f} 元")
    else:
        print(f"文件不存在: {csv_file}")
        df_local = None
    
    # 2. BaoStock数据
    print("\n[2] BaoStock实时数据")
    print("-" * 70)
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return
    
    # 获取股票信息
    rs = bs.query_stock_basic(code=f"sh.{stock_code}")
    stock_info = []
    while rs.next():
        stock_info.append(rs.get_row_data())
    
    if stock_info:
        info_df = pd.DataFrame(stock_info, columns=rs.fields)
        print(f"股票代码: {info_df.iloc[0]['code']}")
        print(f"股票名称: {info_df.iloc[0]['code_name']}")
        print(f"上市状态: {info_df.iloc[0]['ipoDate']}")
    
    # 获取最近数据（前复权）
    print("\n前复权数据（当前使用）:")
    rs = bs.query_history_k_data_plus(
        f"sh.{stock_code}",
        "date,open,high,low,close,volume,amount",
        start_date='2026-02-04',
        end_date='2026-02-06',
        frequency="d",
        adjustflag="2"  # 前复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    if data_list:
        df_qfq = pd.DataFrame(data_list, columns=rs.fields)
        print(df_qfq)
        bs_close = float(df_qfq.iloc[-1]['close'])
        bs_date = df_qfq.iloc[-1]['date']
        print(f"\nBaoStock最新: {bs_date}, 收盘价: {bs_close:.2f} 元")
    else:
        print("无数据")
        bs_close = None
    
    # 获取不复权数据
    print("\n不复权数据（真实价格）:")
    rs = bs.query_history_k_data_plus(
        f"sh.{stock_code}",
        "date,open,high,low,close,volume,amount",
        start_date='2026-02-04',
        end_date='2026-02-06',
        frequency="d",
        adjustflag="3"  # 不复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    if data_list:
        df_no_adj = pd.DataFrame(data_list, columns=rs.fields)
        print(df_no_adj)
        no_adj_close = float(df_no_adj.iloc[-1]['close'])
        print(f"\n真实价格: {no_adj_close:.2f} 元")
    else:
        no_adj_close = None
    
    # 3. 对比分析
    print("\n[3] 数据对比")
    print("-" * 70)
    
    if df_local is not None and bs_close is not None:
        local_close = float(df_local.iloc[-1]['close'])
        
        print(f"本地文件: {local_close:.2f} 元")
        print(f"BaoStock: {bs_close:.2f} 元")
        
        diff = abs(local_close - bs_close)
        if diff < 0.01:
            print("\n[OK] 价格一致！数据正确")
        else:
            diff_pct = (local_close - bs_close) / bs_close * 100
            print(f"\n[WARNING] 价格不一致！")
            print(f"差异: {local_close - bs_close:.2f} 元 ({diff_pct:.2f}%)")
            print("\n可能原因:")
            print("1. 本地是旧的AkShare数据")
            print("2. 复权方式不同")
            print("3. 数据更新时间不同")
    
    # 4. 检查文件创建时间
    if df_local is not None:
        file_time = pd.to_datetime(os.path.getmtime(csv_file), unit='s')
        print("\n[4] 文件信息")
        print("-" * 70)
        print(f"创建/修改时间: {file_time}")
        
        # 如果文件是今天17:36之前的，可能是旧数据
        if file_time.hour < 17 or (file_time.hour == 17 and file_time.minute < 36):
            print("[WARNING] 文件可能是切换数据源之前的旧数据")
        else:
            print("[OK] 文件是最近创建的")
    
    bs.logout()
    
    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    print("""
如果数据不一致，请执行清理：
1. 运行: COMPLETE_CLEANUP.bat
2. 删除所有旧数据
3. 重新下载

数据源说明：
- 当前配置: BaoStock
- 复权方式: 前复权
- 数据准确: 与市场价格一致
""")


if __name__ == '__main__':
    verify_600157()
