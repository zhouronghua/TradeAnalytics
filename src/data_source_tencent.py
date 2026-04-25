"""
腾讯财经数据源
使用腾讯财经API获取股票数据，作为AkShare/BaoStock的替代方案
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import sys
import os
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, safe_read_csv


class TencentDataSource:
    """腾讯财经数据源 - 使用腾讯财经API获取股票数据"""

    def __init__(self):
        self.logger = setup_logger('Tencent')
        # 限流控制 - 每秒最多3个请求
        self._last_request_time = 0
        self._request_lock = threading.Lock()
        self._min_interval = 0.3  # 最少间隔0.3秒

    def _rate_limit(self):
        """请求限流控制"""
        with self._request_lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_interval:
                sleep_time = self._min_interval - elapsed
                time.sleep(sleep_time)
            self._last_request_time = time.time()

    def _get_tencent_code(self, stock_code: str) -> str:
        """
        转换股票代码为腾讯格式

        Args:
            stock_code: 股票代码（6位数字）

        Returns:
            腾讯格式代码（sh600000 或 sz000001）
        """
        if stock_code.startswith('6'):
            return f'sh{stock_code}'
        else:
            return f'sz{stock_code}'

    def get_stock_list(self, stocks_file: str = 'data/stocks/stock_list.csv') -> Optional[pd.DataFrame]:
        """
        获取股票列表
        优先从本地缓存读取，避免重复请求导致IP被封

        Args:
            stocks_file: 股票列表文件路径

        Returns:
            股票列表DataFrame（包含code和name列）
        """
        # 优先从本地缓存读取
        if os.path.exists(stocks_file):
            try:
                df = safe_read_csv(stocks_file, dtype={'code': str})
                if df is not None and not df.empty and 'code' in df.columns:
                    # 确保有name列
                    if 'name' not in df.columns:
                        df['name'] = df['code']
                    self.logger.info(f"从本地缓存读取股票列表: {len(df)} 只")
                    return df[['code', 'name']]
            except Exception as e:
                self.logger.warning(f"读取本地股票列表失败: {e}")

        # 本地缓存不存在或读取失败，返回空DataFrame
        self.logger.warning(f"本地股票列表不可用: {stocks_file}")
        return pd.DataFrame(columns=['code', 'name'])

    def get_stock_history(self, stock_code: str,
                         start_date: str,
                         end_date: str) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据（前复权）
        腾讯API限制每次最多返回500条数据，如需更多数据会自动分段获取

        Args:
            stock_code: 股票代码（6位数字）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            历史数据DataFrame，包含列: date, open, high, low, close, volume, amount
        """
        return self._get_stock_history_chunked(stock_code, start_date, end_date)

    def _get_stock_history_chunked(self, stock_code: str,
                                   start_date: str,
                                   end_date: str) -> Optional[pd.DataFrame]:
        """
        分段获取股票历史数据（处理腾讯API 500条限制）
        """
        tencent_code = self._get_tencent_code(stock_code)
        all_data = []

        # 计算需要分段获取的次数（每段约2年，500个交易日）
        from datetime import datetime as dt
        start_dt = dt.strptime(start_date, '%Y-%m-%d')
        end_dt = dt.strptime(end_date, '%Y-%m-%d')

        # 分段获取数据（每段约2年）
        current_start = start_dt
        max_chunks = 10  # 最多获取10段（约20年，足够覆盖2020年至今）
        chunk_count = 0

        while current_start <= end_dt and chunk_count < max_chunks:
            chunk_count += 1

            # 计算当前段的结束日期（约2年后）
            from dateutil.relativedelta import relativedelta
            current_end = min(current_start + relativedelta(years=2), end_dt)

            chunk_start = current_start.strftime('%Y-%m-%d')
            chunk_end = current_end.strftime('%Y-%m-%d')

            self.logger.debug(f"股票 {stock_code} 获取第 {chunk_count} 段数据: {chunk_start} 至 {chunk_end}")

            # 获取当前段数据
            chunk_df = self._get_stock_history_single(tencent_code, chunk_start, chunk_end)

            if chunk_df is not None and not chunk_df.empty:
                all_data.append(chunk_df)
                self.logger.debug(f"股票 {stock_code} 第 {chunk_count} 段获取 {len(chunk_df)} 条数据")

                # 如果获取的数据少于400条，说明已经到末尾，不需要继续
                if len(chunk_df) < 400:
                    break
            else:
                # 当前段无数据，尝试下一段
                self.logger.debug(f"股票 {stock_code} 第 {chunk_count} 段无数据")

            # 移动到下一段（从当前段最后一天的下一天开始）
            current_start = current_end + timedelta(days=1)

            # 限流：段与段之间也做限流
            if current_start <= end_dt:
                time.sleep(0.3)

        if not all_data:
            return None

        # 合并所有数据
        combined_df = pd.concat(all_data, ignore_index=True)

        # 去重（可能有重叠的日期）
        combined_df.drop_duplicates(subset=['date'], keep='first', inplace=True)

        # 按日期排序
        combined_df.sort_values('date', inplace=True)
        combined_df.reset_index(drop=True, inplace=True)

        self.logger.debug(f"股票 {stock_code} 总计获取 {len(combined_df)} 条数据（分段获取 {chunk_count} 次）")
        return combined_df

    def _get_stock_history_single(self, tencent_code: str,
                                   start_date: str,
                                   end_date: str) -> Optional[pd.DataFrame]:
        """
        单次获取股票历史数据（最多500条）
        """
        self._rate_limit()  # 限流控制

        # 构建API URL
        # 腾讯K线API: param=代码,day,开始日期,结束日期,数量,复权类型
        url = (
            f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            f"?param={tencent_code},day,{start_date},{end_date},500,qfq"
        )

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            data = response.json()

            # 检查返回数据
            if data.get('code') != 0:
                self.logger.warning(f"股票 {tencent_code} 数据获取失败: {data.get('msg', '未知错误')}")
                return None

            # 提取K线数据
            stock_data = data.get('data', {}).get(tencent_code, {})
            kline_data = stock_data.get('qfqday', [])  # 前复权日线数据

            if not kline_data:
                self.logger.debug(f"股票 {tencent_code} 无历史数据 ({start_date} 至 {end_date})")
                return None

            # 转换为DataFrame
            # 腾讯数据格式: [date, open, close, low, high, volume]
            df_data = []
            for item in kline_data:
                if len(item) >= 6:
                    df_data.append({
                        'date': item[0],
                        'open': float(item[1]),
                        'close': float(item[2]),
                        'low': float(item[3]),
                        'high': float(item[4]),
                        'volume': int(float(item[5]))  # 成交量（手）
                    })

            if not df_data:
                return None

            df = pd.DataFrame(df_data)

            # 计算成交额（估算）
            # 成交额 = 成交量(手) * 100 * 均价
            df['amount'] = (df['volume'] * 100 * (df['open'] + df['close']) / 2).astype(int)

            # 转换日期格式
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

            # 按日期排序
            df.sort_values('date', inplace=True)
            df.reset_index(drop=True, inplace=True)

            return df

        except requests.exceptions.Timeout:
            self.logger.warning(f"股票 {tencent_code} 请求超时")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"股票 {tencent_code} 网络错误: {e}")
            return None
        except Exception as e:
            self.logger.error(f"股票 {tencent_code} 数据处理异常: {e}")
            return None

    def test_connection(self) -> bool:
        """测试数据源连接"""
        try:
            df = self.get_stock_history('600000', '2026-04-01', '2026-04-25')
            if df is not None and not df.empty:
                self.logger.info("腾讯数据源连接测试成功")
                return True
        except Exception as e:
            self.logger.error(f"腾讯数据源连接测试失败: {e}")
        return False


def main():
    """测试腾讯数据源"""
    print("=" * 70)
    print("测试腾讯财经数据源")
    print("=" * 70)

    source = TencentDataSource()

    # 测试股票列表
    print("\n[1] 测试获取股票列表...")
    stock_list = source.get_stock_list()
    if stock_list is not None and not stock_list.empty:
        print(f"成功获取 {len(stock_list)} 只股票")
        print(stock_list.head())
    else:
        print("股票列表为空或读取失败")

    # 测试单只股票历史数据
    print("\n[2] 测试获取股票历史数据 (600000)...")
    df = source.get_stock_history('600000', '2026-04-01', '2026-04-25')
    if df is not None and not df.empty:
        print(f"成功获取 {len(df)} 条数据")
        print(df.head())
        print("...")
        print(df.tail())
    else:
        print("获取失败")

    # 测试深圳股票
    print("\n[3] 测试获取深圳股票 (000001)...")
    df2 = source.get_stock_history('000001', '2026-04-01', '2026-04-25')
    if df2 is not None and not df.empty:
        print(f"成功获取 {len(df2)} 条数据")
        print(df2.head())
    else:
        print("获取失败")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
