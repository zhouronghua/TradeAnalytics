"""
验证600343的价格数据
对比文件中的数据和BaoStock实时数据
"""

import pandas as pd
import baostock as bs
import os

def verify_stock_price():
    """验证股票价格"""
    stock_code = "600343"
    csv_file = f"data/daily/{stock_code}.csv"
    
    print("=" * 70)
    print(f"验证 {stock_code} 航天动力 价格数据")
    print("=" * 70)
    
    # 1. 检查本地文件
    print("\n[1] 检查本地CSV文件")
    print("-" * 70)
    
    if os.path.exists(csv_file):
        df_local = pd.read_csv(csv_file)
        print(f"文件存在: {csv_file}")
        print(f"数据行数: {len(df_local)}")
        print(f"最后修改: {pd.to_datetime(os.path.getmtime(csv_file), unit='s')}")
        print("\n最后5行数据:")
        print(df_local.tail())
        
        if len(df_local) > 0:
            last_close = df_local.iloc[-1]['close']
            last_date = df_local.iloc[-1]['date']
            print(f"\n文件中最新数据: {last_date}, 收盘价: {last_close:.2f} 元")
    else:
        print(f"文件不存在: {csv_file}")
        df_local = None
    
    # 2. 从BaoStock获取最新数据
    print("\n[2] 从BaoStock获取最新数据")
    print("-" * 70)
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return
    
    print("BaoStock登录成功")
    
    # 获取最近3天数据
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
    
    df_baostock = pd.DataFrame(data_list, columns=rs.fields)
    
    if not df_baostock.empty:
        print("\nBaoStock最近3天数据:")
        print(df_baostock)
        
        bs_last_close = float(df_baostock.iloc[-1]['close'])
        bs_last_date = df_baostock.iloc[-1]['date']
        print(f"\nBaoStock最新数据: {bs_last_date}, 收盘价: {bs_last_close:.2f} 元")
    
    # 3. 对比
    print("\n[3] 数据对比")
    print("-" * 70)
    
    if df_local is not None and not df_baostock.empty:
        local_close = float(df_local.iloc[-1]['close'])
        
        print(f"本地文件价格: {local_close:.2f} 元")
        print(f"BaoStock价格: {bs_last_close:.2f} 元")
        
        if abs(local_close - bs_last_close) < 0.01:
            print("\n[OK] 价格一致，数据正确！")
        else:
            diff = local_close - bs_last_close
            diff_pct = (diff / bs_last_close) * 100
            print(f"\n[WARNING] 价格不一致！")
            print(f"差异: {diff:.2f} 元 ({diff_pct:.2f}%)")
            print("\n建议:")
            print("1. 运行 clean_old_data.bat 清理旧数据")
            print("2. 重新运行 python main.py 下载正确数据")
    
    # 4. 数据源说明
    print("\n[4] 数据源说明")
    print("-" * 70)
    print("当前配置使用: BaoStock")
    print("复权方式: 前复权（adjustflag=2）")
    print("数据特点: 官方API，稳定可靠")
    
    bs.logout()
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    verify_stock_price()
