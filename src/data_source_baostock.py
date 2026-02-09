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
            
            # 获取所有A股股票，优先使用当天日期
            query_date = datetime.now().strftime('%Y-%m-%d')
            self.logger.info(f"查询日期: {query_date}")
            rs = bs.query_all_stock(day=query_date)
            
            if rs.error_code != '0':
                self.logger.error(f"获取股票列表失败: {rs.error_msg}")
                return None
            
            # 转换为DataFrame
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            stock_list = pd.DataFrame(data_list, columns=rs.fields)
            
            self.logger.info(f"从BaoStock获取到 {len(stock_list)} 条记录")
            self.logger.info(f"字段列表: {list(stock_list.columns)}")
            
            # 检查是否为空，可能是非交易日
            if len(stock_list) == 0:
                self.logger.warning(f"查询日期 {query_date} 返回空数据，可能是非交易日")
                
                # 尝试查询最近的交易日（向前查询最多7天）
                for days_back in range(1, 8):
                    retry_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                    # 跳过周末
                    retry_datetime = datetime.now() - timedelta(days=days_back)
                    if retry_datetime.weekday() >= 5:  # 周六或周日
                        continue
                    
                    self.logger.info(f"尝试查询 {retry_date}...")
                    rs_retry = bs.query_all_stock(day=retry_date)
                    
                    if rs_retry.error_code == '0':
                        data_list_retry = []
                        while rs_retry.next():
                            data_list_retry.append(rs_retry.get_row_data())
                        
                        if len(data_list_retry) > 0:
                            self.logger.info(f"成功从 {retry_date} 获取到 {len(data_list_retry)} 条记录")
                            stock_list = pd.DataFrame(data_list_retry, columns=rs_retry.fields)
                            break
                
                # 如果仍然为空，返回空DataFrame
                if len(stock_list) == 0:
                    self.logger.warning("未能从最近7个工作日获取到股票列表")
                    return pd.DataFrame(columns=['code', 'name'])
            
            # 过滤只保留A股
            if 'code' in stock_list.columns:
                stock_list = stock_list[stock_list['code'].str.match(r'^(?:sh\.|sz\.)', na=False)]
            else:
                self.logger.error(f"返回的数据中没有'code'字段，可用字段: {list(stock_list.columns)}")
                return None
            
            # 标准化格式
            stock_list['code'] = stock_list['code'].str.replace('sh.', '').str.replace('sz.', '')
            
            # 检查并重命名列
            rename_map = {}
            if 'code_name' in stock_list.columns:
                rename_map['code_name'] = 'name'
            if 'tradeStatus' in stock_list.columns:
                rename_map['tradeStatus'] = 'status'
            
            if rename_map:
                stock_list.rename(columns=rename_map, inplace=True)
                self.logger.info(f"列重命名: {rename_map}")
            else:
                self.logger.warning(f"未找到需要重命名的列，当前列: {list(stock_list.columns)}")
            
            # 只保留交易状态为1的股票（正在交易）
            if 'status' in stock_list.columns:
                stock_list = stock_list[stock_list['status'] == '1']
            else:
                self.logger.warning("没有找到'status'字段，无法按交易状态过滤")
            
            self.logger.info(f"获取到 {len(stock_list)} 只股票")
            
            # 检查必需的列是否存在
            if 'code' not in stock_list.columns:
                self.logger.error(f"结果中缺少'code'列，当前列: {list(stock_list.columns)}")
                return None
            
            if 'name' not in stock_list.columns:
                self.logger.warning(f"结果中缺少'name'列，将使用股票代码作为名称")
                stock_list['name'] = stock_list['code']
            
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
