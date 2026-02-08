"""
线程安全的BaoStock数据源
每个线程使用独立的BaoStock连接
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import sys
import os
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger


class ThreadSafeBaoStockDataSource:
    """线程安全的BaoStock数据源"""
    
    def __init__(self):
        self.logger = setup_logger('BaoStock')
        self.local = threading.local()  # 线程本地存储
    
    def _ensure_login(self) -> bool:
        """确保当前线程已登录"""
        if not hasattr(self.local, 'logged_in') or not self.local.logged_in:
            try:
                lg = bs.login()
                if lg.error_code == '0':
                    self.local.logged_in = True
                    thread_id = threading.current_thread().name
                    self.logger.debug(f"线程 {thread_id} BaoStock登录成功")
                    return True
                else:
                    self.logger.error(f"BaoStock登录失败: {lg.error_msg}")
                    return False
            except Exception as e:
                self.logger.error(f"BaoStock登录异常: {e}")
                return False
        return True
    
    def _ensure_logout(self):
        """确保当前线程登出"""
        if hasattr(self.local, 'logged_in') and self.local.logged_in:
            try:
                bs.logout()
                self.local.logged_in = False
                thread_id = threading.current_thread().name
                self.logger.debug(f"线程 {thread_id} BaoStock已登出")
            except Exception as e:
                self.logger.debug(f"登出异常: {e}")
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表
        
        Returns:
            股票列表DataFrame
        """
        if not self._ensure_login():
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
            
            self.logger.info(f"从BaoStock获取到 {len(stock_list)} 条记录")
            self.logger.info(f"字段列表: {list(stock_list.columns)}")
            
            # 检查是否为空
            if len(stock_list) == 0:
                self.logger.warning("BaoStock返回的股票列表为空")
                return pd.DataFrame(columns=['code', 'name'])
            
            # 过滤只保留A股（上交所和深交所）
            if 'code' in stock_list.columns:
                stock_list = stock_list[stock_list['code'].str.contains(r'^(sh\.|sz\.)', regex=True)]
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
            
            # 检查是否有type字段，如果有则只保留股票类型
            if 'type' in stock_list.columns:
                original_count = len(stock_list)
                # type=1 表示股票，type=2 表示指数，type=3 表示其他
                stock_list = stock_list[stock_list['type'] == '1']
                filtered_by_type = original_count - len(stock_list)
                if filtered_by_type > 0:
                    self.logger.info(f"根据type字段过滤 {filtered_by_type} 只非股票（指数等）")
            
            # 只保留交易状态为1的股票（正在交易）
            if 'status' in stock_list.columns:
                stock_list = stock_list[stock_list['status'] == '1']
            else:
                self.logger.warning("没有找到'status'字段，无法按交易状态过滤")
            
            # 精确过滤：只保留股票代码，排除基金、债券、指数等
            # 上交所股票：60xxxx, 68xxxx（科创板）
            # 深交所股票：002xxx, 003xxx（主板和中小板）, 300xxx（创业板）
            # 注意：000001-000999范围内有大量指数，需要排除
            def is_valid_stock(code):
                if len(code) != 6:
                    return False
                # 上交所：60, 68开头
                if code.startswith('60') or code.startswith('68'):
                    return True
                # 深交所中小板：002, 003开头
                if code.startswith('002') or code.startswith('003'):
                    return True
                # 深交所创业板：300开头
                if code.startswith('300'):
                    return True
                # 深交所主板：001开头（较新）
                if code.startswith('001'):
                    return True
                return False
            
            original_count = len(stock_list)
            stock_list = stock_list[stock_list['code'].apply(is_valid_stock)]
            filtered_count = original_count - len(stock_list)
            
            if filtered_count > 0:
                self.logger.info(f"代码规则过滤 {filtered_count} 只证券（基金、债券、指数等）")
            
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
        获取股票历史数据（线程安全）
        
        Args:
            stock_code: 股票代码（6位数字）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        
        Returns:
            历史数据DataFrame
        """
        if not self._ensure_login():
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
    
    def cleanup(self):
        """清理当前线程的连接"""
        self._ensure_logout()


def test_thread_safety():
    """测试线程安全性"""
    import time
    
    print("=" * 70)
    print("测试线程安全的BaoStock")
    print("=" * 70)
    
    source = ThreadSafeBaoStockDataSource()
    
    def download_stock(stock_code):
        """在线程中下载股票"""
        thread_name = threading.current_thread().name
        print(f"[{thread_name}] 开始下载 {stock_code}")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        df = source.get_stock_history(stock_code, start_date, end_date)
        
        if df is not None:
            print(f"[{thread_name}] {stock_code} 成功: {len(df)} 天")
            # 验证数据（检查日期列）
            if 'date' in df.columns and len(df) > 0:
                first_date = df.iloc[0]['date']
                last_date = df.iloc[-1]['date']
                print(f"[{thread_name}] {stock_code} 日期范围: {first_date} - {last_date}")
            return True
        else:
            print(f"[{thread_name}] {stock_code} 失败")
            return False
    
    # 测试多线程
    test_stocks = ['000001', '600000', '000002', '600001', '000004']
    
    print("\n测试1：单线程（对照组）")
    print("-" * 70)
    for stock in test_stocks[:2]:
        download_stock(stock)
        time.sleep(1)
    
    print("\n测试2：多线程（3个并发）")
    print("-" * 70)
    threads = []
    for stock in test_stocks:
        t = threading.Thread(target=download_stock, args=(stock,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("如果看到正确的日期范围，说明线程安全")
    print("=" * 70)


if __name__ == '__main__':
    test_thread_safety()
