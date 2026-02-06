"""
BaoStock数据源
作为AkShare的备用数据源
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger


class BaoStockDataSource:
    """BaoStock数据源"""
    
    def __init__(self):
        self.logger = setup_logger('BaoStock')
        self.logged_in = False
    
    def login(self) -> bool:
        """登录BaoStock"""
        try:
            lg = bs.login()
            if lg.error_code == '0':
                self.logged_in = True
                self.logger.info("BaoStock登录成功")
                return True
            else:
                self.logger.error(f"BaoStock登录失败: {lg.error_msg}")
                return False
        except Exception as e:
            self.logger.error(f"BaoStock登录异常: {e}")
            return False
    
    def logout(self):
        """登出BaoStock"""
        if self.logged_in:
            bs.logout()
            self.logged_in = False
            self.logger.info("BaoStock已登出")
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表
        
        Returns:
            股票列表DataFrame
        """
        if not self.logged_in:
            if not self.login():
                return None
        
        try:
            self.logger.info("从BaoStock获取股票列表...")
            
            # 获取所有A股股票
            rs = bs.query_all_stock(day=datetime.now().strftime('%Y-%m-%d'))
            
            if rs.error_code != '0':
                self.logger.error(f"获取股票列表失败: {rs.error_msg}")
                return None
            
            # 转换为DataFrame
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            stock_list = pd.DataFrame(data_list, columns=rs.fields)
            
            # 过滤只保留A股
            stock_list = stock_list[stock_list['code'].str.contains(r'^(sh\.|sz\.)', regex=True)]
            
            # 标准化格式
            stock_list['code'] = stock_list['code'].str.replace('sh.', '').str.replace('sz.', '')
            stock_list.rename(columns={
                'code': 'code',
                'code_name': 'name',
                'tradeStatus': 'status'
            }, inplace=True)
            
            # 只保留交易状态为1的股票（正在交易）
            stock_list = stock_list[stock_list['status'] == '1']
            
            self.logger.info(f"获取到 {len(stock_list)} 只股票")
            return stock_list[['code', 'name']]
            
        except Exception as e:
            self.logger.error(f"获取股票列表异常: {e}")
            return None
    
    def get_stock_history(self, stock_code: str, start_date: str, 
                         end_date: str) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码（6位数字）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            历史数据DataFrame
        """
        if not self.logged_in:
            if not self.login():
                return None
        
        try:
            # 添加市场前缀
            if stock_code.startswith('6'):
                bs_code = f'sh.{stock_code}'
            else:
                bs_code = f'sz.{stock_code}'
            
            # 获取日K线数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",  # 日线
                adjustflag="2"  # 前复权
            )
            
            if rs.error_code != '0':
                self.logger.warning(f"股票 {stock_code} 数据获取失败: {rs.error_msg}")
                return None
            
            # 转换为DataFrame
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return None
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype('int64')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype('int64')
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取股票 {stock_code} 数据异常: {e}")
            return None


def main():
    """测试BaoStock"""
    print("测试BaoStock数据源...")
    
    bs_source = BaoStockDataSource()
    
    # 测试登录
    if bs_source.login():
        print("[OK] 登录成功")
        
        # 测试获取股票列表
        stock_list = bs_source.get_stock_list()
        if stock_list is not None:
            print(f"[OK] 获取股票列表成功: {len(stock_list)} 只")
            print(stock_list.head())
            
            # 测试获取单只股票数据
            test_code = stock_list.iloc[0]['code']
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d')
            
            df = bs_source.get_stock_history(test_code, start_date, end_date)
            if df is not None:
                print(f"\n[OK] 获取股票 {test_code} 数据成功: {len(df)} 天")
                print(df.tail())
        
        bs_source.logout()
    else:
        print("[FAIL] 登录失败")


if __name__ == '__main__':
    main()
