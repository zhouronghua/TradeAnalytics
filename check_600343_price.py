"""
检查600343的价格差异问题
对比前复权和不复权数据
"""

import baostock as bs
import pandas as pd

def check_price_difference():
    """检查价格差异"""
    print("=" * 70)
    print("600343 航天动力 - 价格差异分析")
    print("=" * 70)
    
    # 登录BaoStock
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return
    
    print("\n[OK] BaoStock登录成功")
    
    # 获取前复权数据（adjustflag="2"）
    print("\n1. 前复权数据（当前使用）:")
    print("-" * 70)
    rs = bs.query_history_k_data_plus(
        "sh.600343",
        "date,open,high,low,close,volume,amount",
        start_date='2026-02-05',
        end_date='2026-02-06',
        frequency="d",
        adjustflag="2"  # 前复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    df_qfq = pd.DataFrame(data_list, columns=rs.fields)
    print(df_qfq)
    
    # 获取不复权数据（adjustflag="3"）
    print("\n2. 不复权数据（真实价格）:")
    print("-" * 70)
    rs = bs.query_history_k_data_plus(
        "sh.600343",
        "date,open,high,low,close,volume,amount",
        start_date='2026-02-05',
        end_date='2026-02-06',
        frequency="d",
        adjustflag="3"  # 不复权
    )
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    df_no_adjust = pd.DataFrame(data_list, columns=rs.fields)
    print(df_no_adjust)
    
    # 计算差异
    if not df_qfq.empty and not df_no_adjust.empty:
        qfq_close = float(df_qfq.iloc[-1]['close'])
        no_adjust_close = float(df_no_adjust.iloc[-1]['close'])
        
        print("\n" + "=" * 70)
        print("价格对比")
        print("=" * 70)
        print(f"前复权价格（文件中的数据）: {qfq_close:.2f} 元")
        print(f"不复权价格（真实价格）  : {no_adjust_close:.2f} 元")
        print(f"差异: {qfq_close - no_adjust_close:.2f} 元 ({(qfq_close/no_adjust_close - 1)*100:.2f}%)")
        
        print("\n" + "=" * 70)
        print("原因分析")
        print("=" * 70)
        print("""
前复权（当前使用）：
- 调整了历史价格，使图表连续
- 便于技术分析和指标计算
- 价格不是真实历史价格

不复权（真实价格）：
- 显示真实历史价格
- 会因分红配股出现跳空
- 不利于技术分析

建议：
- 技术分析、均线计算 → 使用前复权（当前设置）✓
- 查看真实价格 → 需要改为不复权
""")
    
    # 查询分红配股信息
    print("\n" + "=" * 70)
    print("分红配股历史")
    print("=" * 70)
    rs = bs.query_dividend_data(code="sh.600343", year="2025", yearType="report")
    
    dividend_list = []
    while rs.next():
        dividend_list.append(rs.get_row_data())
    
    if dividend_list:
        df_dividend = pd.DataFrame(dividend_list, columns=rs.fields)
        print(df_dividend[['dividOperateDate', 'dividPreNoticeDate', 'dividAgmPumDate', 
                          'dividPlanAnnounceDate', 'dividStockMarketDate']])
    else:
        print("2025年暂无分红配股记录")
    
    bs.logout()


if __name__ == '__main__':
    check_price_difference()
