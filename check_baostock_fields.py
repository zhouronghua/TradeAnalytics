"""
检查BaoStock返回的股票列表字段
查看是否有字段可以区分指数和股票
"""

import baostock as bs
import pandas as pd
from datetime import datetime

def check_fields():
    print("检查BaoStock股票列表字段...")
    
    # 登录
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return
    
    print("登录成功\n")
    
    # 获取股票列表
    rs = bs.query_all_stock(day=datetime.now().strftime('%Y-%m-%d'))
    
    print(f"字段列表: {rs.fields}\n")
    
    # 查看前100条数据
    data_list = []
    count = 0
    while rs.next() and count < 100:
        data_list.append(rs.get_row_data())
        count += 1
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    
    print("前100条数据样本:")
    print("=" * 100)
    print(df.to_string())
    
    print("\n\n数据类型分布:")
    print("=" * 100)
    if 'type' in df.columns:
        print("\ntype 字段分布:")
        print(df['type'].value_counts())
    
    if 'code' in df.columns:
        print("\n\n代码前缀分布:")
        df['prefix'] = df['code'].str[:5]
        print(df['prefix'].value_counts().head(20))
    
    # 登出
    bs.logout()
    print("\n\n登出成功")


if __name__ == '__main__':
    check_fields()
