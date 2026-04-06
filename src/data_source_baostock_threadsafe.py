"""
线程安全的BaoStock数据源
使用锁串行化baostock的全局操作，实现真正的多线程安全
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import sys
import os
import threading
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, format_date


class ThreadSafeBaoStockDataSource:
    """线程安全的BaoStock数据源 - 使用全局锁实现多线程安全"""

    # 全局锁，用于串行化所有baostock操作
    _global_lock = threading.Lock()
    _global_logged_in = False
    _global_login_time = None
    _login_timeout = 300  # 登录超时5分钟

    def __init__(self):
        self.logger = setup_logger('BaoStock')

    def _ensure_login(self) -> bool:
        """确保已登录（全局锁保护）"""
        with ThreadSafeBaoStockDataSource._global_lock:
            # 检查是否已登录且未超时
            if ThreadSafeBaoStockDataSource._global_logged_in:
                if ThreadSafeBaoStockDataSource._global_login_time:
                    elapsed = time.time() - ThreadSafeBaoStockDataSource._global_login_time
                    if elapsed < self._login_timeout:
                        return True
                    else:
                        # 超时，先登出
                        self._logout_internal()

            # 执行登录
            try:
                lg = bs.login()
                if lg.error_code == '0':
                    ThreadSafeBaoStockDataSource._global_logged_in = True
                    ThreadSafeBaoStockDataSource._global_login_time = time.time()
                    self.logger.debug(f"BaoStock全局登录成功")
                    return True
                else:
                    self.logger.error(f"BaoStock登录失败: {lg.error_msg}")
                    return False
            except Exception as e:
                self.logger.error(f"BaoStock登录异常: {e}")
                return False

    def _logout_internal(self):
        """内部登出（不加锁，调用者需持有锁）"""
        try:
            bs.logout()
        except:
            pass
        ThreadSafeBaoStockDataSource._global_logged_in = False
        ThreadSafeBaoStockDataSource._global_login_time = None

    def _execute_with_lock(self, func, *args, **kwargs):
        """
        在全局锁保护下执行baostock操作

        流程：
        1. 获取锁
        2. 确保登录
        3. 执行操作
        4. 释放锁
        """
        with ThreadSafeBaoStockDataSource._global_lock:
            if not self._ensure_login():
                return None
            return func(*args, **kwargs)

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表（线程安全）
        """
        def _query():
            query_date = datetime.now().strftime('%Y-%m-%d')
            rs = bs.query_all_stock(day=query_date)

            if rs.error_code != '0':
                return None, rs.error_msg

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            return pd.DataFrame(data_list, columns=rs.fields), None

        result, error = self._execute_with_lock(_query)

        if error:
            self.logger.error(f"获取股票列表失败: {error}")
            return None

        if result is None or result.empty:
            # 尝试查询最近的交易日
            for days_back in range(1, 8):
                retry_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                retry_datetime = datetime.now() - timedelta(days=days_back)
                if retry_datetime.weekday() >= 5:
                    continue

                def _retry_query():
                    rs = bs.query_all_stock(day=retry_date)
                    if rs.error_code != '0':
                        return None, rs.error_msg
                    data_list = []
                    while rs.next():
                        data_list.append(rs.get_row_data())
                    return pd.DataFrame(data_list, columns=rs.fields), None

                result, error = self._execute_with_lock(_retry_query)
                if result is not None and not result.empty:
                    break

        if result is None or result.empty:
            return pd.DataFrame(columns=['code', 'name'])

        # 过滤只保留A股
        if 'code' in result.columns:
            result = result[result['code'].str.match(r'^(?:sh\.|sz\.)', na=False)]

        # 标准化格式
        result['code'] = result['code'].str.replace('sh.', '').str.replace('sz.', '')

        # 过滤有效股票代码
        def is_valid_stock(code):
            if len(code) != 6:
                return False
            if code.startswith('60') or code.startswith('68'):
                return True
            if code.startswith('002') or code.startswith('003'):
                return True
            if code.startswith('300'):
                return True
            if code.startswith('001'):
                return True
            return False

        result = result[result['code'].apply(is_valid_stock)]

        # 标准化列名
        if 'code_name' in result.columns:
            result = result.rename(columns={'code_name': 'name'})
        elif 'name' not in result.columns:
            result['name'] = result['code']

        self.logger.info(f"获取到 {len(result)} 只股票")
        return result[['code', 'name']]

    def get_stock_history(self, stock_code: str,
                         start_date: str,
                         end_date: str) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据（线程安全）
        """
        def _query():
            # 添加市场前缀
            if stock_code.startswith('6'):
                bs_code = f'sh.{stock_code}'
            else:
                bs_code = f'sz.{stock_code}'

            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2"  # 前复权
            )

            if rs.error_code != '0':
                return None, rs.error_msg

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return None, None

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 转换数据类型
            for col in ['open', 'high', 'low', 'close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype('int64')
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype('int64')

            return df, None

        result, error = self._execute_with_lock(_query)

        if error:
            self.logger.warning(f"股票 {stock_code} 数据获取失败: {error}")
            return None

        return result

    def cleanup(self):
        """清理连接（线程安全）"""
        with ThreadSafeBaoStockDataSource._global_lock:
            self._logout_internal()


def test_multithreaded():
    """测试多线程下载"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    print("=" * 70)
    print("测试BaoStock多线程下载（5线程并发）")
    print("=" * 70)

    source = ThreadSafeBaoStockDataSource()

    # 测试股票列表
    test_stocks = ['600000', '000001', '600001', '000002', '600825',
                   '600826', '600827', '600828', '600829', '600830']

    start_time = time.time()
    results = {'success': 0, 'failed': 0}

    def download_one(code):
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            df = source.get_stock_history(code, start_date, end_date)
            if df is not None and not df.empty:
                return code, True, len(df)
            else:
                return code, False, 0
        except Exception as e:
            return code, False, str(e)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_one, code): code for code in test_stocks}

        for future in as_completed(futures):
            code, success, info = future.result()
            if success:
                results['success'] += 1
                print(f"✓ {code}: {info} 条数据")
            else:
                results['failed'] += 1
                print(f"✗ {code}: 失败 ({info})")

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"结果: 成功 {results['success']}, 失败 {results['failed']}, 耗时 {elapsed:.2f} 秒")
    print("=" * 70)

    source.cleanup()


if __name__ == '__main__':
    test_multithreaded()
