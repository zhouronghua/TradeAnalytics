"""
Tushare Pro 数据源模块
支持股票历史数据下载，自动处理限频
"""

import pandas as pd
import time
import os
from datetime import datetime, timedelta
from typing import Optional


class TushareDataSource:
    """Tushare Pro 数据源"""

    def __init__(self, token: str = None):
        """
        初始化Tushare数据源

        Args:
            token: Tushare Pro API Token，如果不提供则从环境变量获取
        """
        self.token = token or os.environ.get('TUSHARE_TOKEN')
        self.pro = None
        self.logger = None

        if not self.token:
            raise ValueError("请提供Tushare Token或在环境变量TUSHARE_TOKEN中设置")

        try:
            import tushare as ts
            self.pro = ts.pro_api(self.token)
            # 设置日志
            import logging
            self.logger = logging.getLogger('TushareDataSource')
        except ImportError:
            raise ImportError("请安装tushare: pip install tushare")

        # 限频控制
        self.last_call_time = 0
        self.min_interval = 0.05  # 每秒最多20次调用

    def _rate_limit(self):
        """限频控制"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表

        Returns:
            股票列表DataFrame
        """
        try:
            self._rate_limit()

            # 获取上市股票列表
            df = self.pro.stock_basic(exchange='', list_status='L',
                                     fields='ts_code,symbol,name,area,industry,list_date')

            if df is None or df.empty:
                return None

            # 标准化列名
            df.rename(columns={
                'ts_code': 'code',
                'symbol': 'symbol',
                'name': 'name',
                'area': 'area',
                'industry': 'industry',
                'list_date': 'list_date'
            }, inplace=True)

            # 提取纯数字代码
            df['code'] = df['code'].str.split('.').str[0]

            # 添加市场标识
            df['market'] = df['code'].apply(self._get_market)

            self.logger.info(f"获取到 {len(df)} 只股票")
            return df

        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            return None

    def _get_market(self, code: str) -> str:
        """根据代码判断市场"""
        if code.startswith('6'):
            return 'SH'
        elif code.startswith(('0', '3')):
            return 'SZ'
        elif code.startswith(('4', '8')):
            return 'BJ'
        return 'UNKNOWN'

    def get_stock_history(self, stock_code: str,
                         start_date: str = None,
                         end_date: str = None,
                         adjust: str = 'qfq') -> Optional[pd.DataFrame]:
        """
        获取股票历史日线数据

        Args:
            stock_code: 股票代码（如 '000001'）
            start_date: 开始日期 'YYYYMMDD' 或 'YYYY-MM-DD'
            end_date: 结束日期 'YYYYMMDD' 或 'YYYY-MM-DD'
            adjust: 复权类型 ('qfq'=前复权, 'hfq'=后复权, None=不复权)

        Returns:
            历史数据DataFrame
        """
        try:
            # 转换日期格式
            if start_date and '-' not in start_date:
                start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            if end_date and '-' not in end_date:
                end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            # 默认日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')

            # 构建ts_code
            market = self._get_market(stock_code)
            ts_code = f"{stock_code}.{market}"

            # 复权参数
            adj_flag = None
            if adjust == 'qfq':
                adj_flag = '1'  # 前复权
            elif adjust == 'hfq':
                adj_flag = '2'  # 后复权

            self._rate_limit()

            # 调用Tushare API
            if adj_flag:
                # 使用复权接口
                df = self.pro.pro_bar(ts_code=ts_code, adj=adj_flag,
                                     start_date=start_date, end_date=end_date,
                                     freq='D')
            else:
                # 使用不复权接口
                df = self.pro.daily(ts_code=ts_code,
                                  start_date=start_date, end_date=end_date)

            if df is None or df.empty:
                return None

            # 标准化列名
            column_map = {
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'amount': 'amount',
                'pre_close': 'pre_close',
                'change': 'change',
                'pct_chg': 'change_pct',
            }

            # 重命名存在的列
            available_cols = {k: v for k, v in column_map.items() if k in df.columns}
            df = df.rename(columns=available_cols)

            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')

            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)

            # 确保数值列正确
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'change_pct']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            return df

        except Exception as e:
            if self.logger:
                self.logger.error(f"获取 {stock_code} 历史数据失败: {e}")
            return None

    def get_daily_basic(self, stock_code: str, trade_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取每日指标（换手率、量比等）

        Args:
            stock_code: 股票代码
            trade_date: 交易日期 'YYYYMMDD'

        Returns:
            每日指标DataFrame
        """
        try:
            market = self._get_market(stock_code)
            ts_code = f"{stock_code}.{market}"

            self._rate_limit()

            if trade_date:
                df = self.pro.daily_basic(ts_code=ts_code, trade_date=trade_date)
            else:
                # 获取最近一天
                df = self.pro.daily_basic(ts_code=ts_code)

            return df

        except Exception as e:
            if self.logger:
                self.logger.error(f"获取 {stock_code} 每日指标失败: {e}")
            return None

    def get_trade_calendar(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取交易日历

        Args:
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'

        Returns:
            交易日历DataFrame
        """
        try:
            self._rate_limit()

            df = self.pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
            return df

        except Exception as e:
            if self.logger:
                self.logger.error(f"获取交易日历失败: {e}")
            return None

    def get_limit_up_stocks(self, trade_date: str) -> Optional[pd.DataFrame]:
        """
        获取每日涨停股票列表

        Args:
            trade_date: 交易日期 'YYYYMMDD'

        Returns:
            涨停股票DataFrame
        """
        try:
            self._rate_limit()

            df = self.pro.limit_list(trade_date=trade_date)
            return df

        except Exception as e:
            if self.logger:
                self.logger.error(f"获取涨停列表失败: {e}")
            return None
