#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
妖股策略回测 - 基于2020年以来的完整历史数据
买入规则:
1. 信号日次日开盘价买入
2. 如果开盘涨停(秒板)，延后1天再试，最多延后3天
3. 持有期分别计算5日、10日、20日收益
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from collections import defaultdict

# 添加src到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger, safe_read_csv
from src.monster_stock_analyzer import MonsterStockAnalyzer
from src.data_downloader import DataDownloader


@dataclass
class TradeSignal:
    """交易信号"""
    date: pd.Timestamp          # 信号日期
    stock_code: str             # 股票代码
    stock_name: str             # 股票名称
    score: float                # 妖股评分
    buy_price: float            # 买入价格
    buy_date: pd.Timestamp      # 买入日期
    max_delay: int = 3          # 最大延后天数


@dataclass
class TradeResult:
    """交易结果"""
    signal: TradeSignal
    actual_buy_price: float     # 实际买入价格
    actual_buy_date: pd.Timestamp  # 实际买入日期
    days_delayed: int         # 延后买入的天数
    returns_5d: Optional[float] = None
    returns_10d: Optional[float] = None
    returns_20d: Optional[float] = None
    exit_price_5d: Optional[float] = None
    exit_price_10d: Optional[float] = None
    exit_price_20d: Optional[float] = None
    exit_date_5d: Optional[pd.Timestamp] = None
    exit_date_10d: Optional[pd.Timestamp] = None
    exit_date_20d: Optional[pd.Timestamp] = None


class MonsterStockBacktest:
    """妖股策略回测引擎"""

    def __init__(self, data_dir: str = './data/daily',
                 lookback_days: int = 60,
                 min_score: float = 80.0,
                 config_file: str = 'config/config.ini'):
        self.data_dir = data_dir
        self.lookback_days = lookback_days
        self.min_score = min_score
        self.logger = setup_logger('MonsterStockBacktest')

        # 初始化分析器
        self.analyzer = MonsterStockAnalyzer(config_file)

        # 加载股票列表
        self.stock_list = self._load_stock_list()

        # 缓存股票数据
        self._data_cache = {}

    def _load_stock_list(self) -> pd.DataFrame:
        """加载股票列表"""
        stocks_file = os.path.join(os.path.dirname(self.data_dir), 'stocks', 'stock_list.csv')
        if os.path.exists(stocks_file):
            df = safe_read_csv(stocks_file, dtype={'code': str})
            if df is not None and not df.empty:
                return df

        # 如果没有股票列表，扫描数据目录
        codes = []
        for f in os.listdir(self.data_dir):
            if f.endswith('.csv'):
                codes.append(f.replace('.csv', ''))
        return pd.DataFrame({'code': codes})

    def load_stock_data(self, stock_code: str,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """加载股票历史数据"""
        cache_key = f"{stock_code}_{start_date}_{end_date}"

        if cache_key in self._data_cache:
            return self._data_cache[cache_key]

        file_path = os.path.join(self.data_dir, f"{stock_code}.csv")

        if not os.path.exists(file_path):
            return None

        df = safe_read_csv(file_path)
        if df is None or df.empty:
            return None

        # 转换日期
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        # 确保数值列
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 过滤日期范围
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]

        if len(df) < self.lookback_days:
            return None

        self._data_cache[cache_key] = df
        return df

    def is_limit_up_open(self, df: pd.DataFrame, idx: int,
                         prev_close: float) -> bool:
        """
        判断是否开盘涨停（秒板）

        涨停判断标准:
        - 普通股票: 涨幅 >= 9.9%
        - ST股票: 涨幅 >= 4.9%
        """
        if idx >= len(df):
            return False

        open_price = df.iloc[idx]['open']

        # 计算涨停幅度
        limit_pct = 0.099  # 默认9.9%
        # 检查是否为ST股票（通过涨跌幅限制判断）
        if 'name' in df.columns and idx > 0:
            # 如果之前有涨停限制为5%，则为ST股
            pass

        # 开盘涨幅
        open_pct = (open_price - prev_close) / prev_close if prev_close > 0 else 0

        return open_pct >= limit_pct - 0.001  # 允许微小误差

    def find_buy_point(self, df: pd.DataFrame, signal_idx: int,
                       signal_date: pd.Timestamp,
                       max_delay: int = 3) -> Tuple[Optional[float], Optional[pd.Timestamp], int]:
        """
        寻找实际买入点

        规则:
        1. 信号次日开盘价买入
        2. 如果开盘涨停，延后1天再试
        3. 最多延后max_delay天

        Returns:
            (买入价格, 买入日期, 延后天数) 或 (None, None, -1)
        """
        signal_close = df.iloc[signal_idx]['close']

        # 从次日开始尝试
        for delay in range(max_delay + 1):
            buy_idx = signal_idx + 1 + delay

            if buy_idx >= len(df):
                return None, None, -1

            buy_date = df.iloc[buy_idx]['date']
            open_price = df.iloc[buy_idx]['open']

            # 检查是否开盘涨停
            if delay < max_delay and self.is_limit_up_open(df, buy_idx, signal_close):
                self.logger.debug(f"  {signal_date.strftime('%Y-%m-%d')} 延后{delay+1}天买入: "
                                f"{buy_date.strftime('%Y-%m-%d')}开盘涨停({open_price:.2f}, "
                                f"前收{signal_close:.2f})")
                continue

            # 可以买入
            return open_price, buy_date, delay

        # 超过最大延后天数仍未买到
        return None, None, -1

    def calculate_returns(self, df: pd.DataFrame, buy_idx: int,
                         buy_price: float) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, pd.Timestamp]]:
        """
        计算持有期收益

        Args:
            df: 股票数据
            buy_idx: 买入索引
            buy_price: 买入价格

        Returns:
            (收益率字典, 卖出价格字典, 卖出日期字典)
        """
        hold_periods = [5, 10, 20]
        returns = {}
        exit_prices = {}
        exit_dates = {}

        for period in hold_periods:
            exit_idx = buy_idx + period

            if exit_idx >= len(df):
                # 数据不足，标记为None
                returns[period] = None
                exit_prices[period] = None
                exit_dates[period] = None
            else:
                exit_price = df.iloc[exit_idx]['close']
                exit_date = df.iloc[exit_idx]['date']

                ret = (exit_price - buy_price) / buy_price if buy_price > 0 else 0

                returns[period] = ret
                exit_prices[period] = exit_price
                exit_dates[period] = exit_date

        return returns, exit_prices, exit_dates

    def analyze_single_stock(self, stock_code: str,
                            start_date: str,
                            end_date: str) -> List[TradeResult]:
        """
        分析单只股票的回测结果

        Returns:
            交易结果列表
        """
        results = []

        # 加载数据（需要足够的历史数据计算指标）
        data_start = (pd.to_datetime(start_date) - timedelta(days=self.lookback_days * 2)).strftime('%Y-%m-%d')
        df = self.load_stock_data(stock_code, start_date=data_start, end_date=end_date)

        if df is None or len(df) < self.lookback_days + 20:  # 需要足够数据计算收益
            return results

        # 获取股票名称
        stock_name = ""
        if self.stock_list is not None:
            match = self.stock_list[self.stock_list['code'] == stock_code]
            if not match.empty and 'name' in match.columns:
                stock_name = match.iloc[0]['name']

        # 遍历每一天检测信号
        for idx in range(self.lookback_days, len(df) - 20):  # 留20天计算收益
            current_date = df.iloc[idx]['date']

            # 只在回测日期范围内处理
            if current_date < pd.to_datetime(start_date) or current_date > pd.to_datetime(end_date):
                continue

            # 获取历史数据用于分析
            lookback_df = df.iloc[idx - self.lookback_days:idx + 1].copy()

            # 需要保存到临时文件（因为analyzer使用文件路径）
            temp_file = f'/tmp/monster_analysis_{stock_code}_{idx}.csv'
            lookback_df.to_csv(temp_file, index=False)

            try:
                # 使用妖股分析器检测信号
                score_data = self.analyzer.analyze_single(temp_file, stock_code)

                if score_data is not None and score_data.get('score', 0) >= self.min_score:
                    score = score_data['score']
                    signal_date = current_date

                    # 寻找买入点
                    buy_price, buy_date, delay = self.find_buy_point(
                        df, idx, signal_date, max_delay=3
                    )

                    if buy_price is None:
                        self.logger.debug(f"{stock_code} {signal_date.strftime('%Y-%m-%d')} "
                                        f"未找到买入点（延后超过3天）")
                        continue

                    # 计算收益
                    buy_idx = df[df['date'] == buy_date].index[0]
                    returns, exit_prices, exit_dates = self.calculate_returns(df, buy_idx, buy_price)

                    # 创建交易结果
                    signal = TradeSignal(
                        date=signal_date,
                        stock_code=stock_code,
                        stock_name=stock_name,
                        score=score,
                        buy_price=buy_price,
                        buy_date=buy_date,
                        max_delay=3
                    )

                    result = TradeResult(
                        signal=signal,
                        actual_buy_price=buy_price,
                        actual_buy_date=buy_date,
                        days_delayed=delay,
                        returns_5d=returns.get(5),
                        returns_10d=returns.get(10),
                        returns_20d=returns.get(20),
                        exit_price_5d=exit_prices.get(5),
                        exit_price_10d=exit_prices.get(10),
                        exit_price_20d=exit_prices.get(20),
                        exit_date_5d=exit_dates.get(5),
                        exit_date_10d=exit_dates.get(10),
                        exit_date_20d=exit_dates.get(20)
                    )

                    results.append(result)

                    self.logger.info(f"信号 {stock_code} {signal_date.strftime('%Y-%m-%d')} "
                                   f"评分:{score:.1f} 买入:{buy_date.strftime('%Y-%m-%d')}@{buy_price:.2f} "
                                   f"延后:{delay}天 "
                                   f"5日:{returns.get(5, 0)*100:.1f}% "
                                   f"10日:{returns.get(10, 0)*100:.1f}% "
                                   f"20日:{returns.get(20, 0)*100:.1f}%")

            except Exception as e:
                self.logger.error(f"分析 {stock_code} {current_date.strftime('%Y-%m-%d')} 异常: {e}")

            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        return results

    def run_backtest(self, start_date: str = '2020-01-01',
                    end_date: Optional[str] = None,
                    sample_stocks: Optional[List[str]] = None) -> pd.DataFrame:
        """
        运行回测

        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期（默认今天）
            sample_stocks: 指定股票列表（None则全部）

        Returns:
            回测结果DataFrame
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        self.logger.info(f"开始回测: {start_date} 至 {end_date}")
        self.logger.info(f"参数: lookback_days={self.lookback_days}, min_score={self.min_score}")

        # 确定股票列表
        if sample_stocks:
            stock_codes = sample_stocks
        else:
            stock_codes = []
            for f in os.listdir(self.data_dir):
                if f.endswith('.csv'):
                    stock_codes.append(f.replace('.csv', ''))

        self.logger.info(f"共 {len(stock_codes)} 只股票待分析")

        all_results = []

        # 遍历每只股票
        for i, code in enumerate(stock_codes):
            if (i + 1) % 100 == 0:
                self.logger.info(f"进度: {i+1}/{len(stock_codes)}")

            try:
                results = self.analyze_single_stock(code, start_date, end_date)
                all_results.extend(results)
            except Exception as e:
                self.logger.error(f"分析股票 {code} 异常: {e}")

        # 转换为DataFrame
        if not all_results:
            self.logger.warning("未找到任何交易信号")
            return pd.DataFrame()

        records = []
        for r in all_results:
            records.append({
                'signal_date': r.signal.date,
                'stock_code': r.signal.stock_code,
                'stock_name': r.signal.stock_name,
                'score': r.signal.score,
                'buy_date': r.actual_buy_date,
                'buy_price': r.actual_buy_price,
                'days_delayed': r.days_delayed,
                'return_5d': r.returns_5d,
                'return_10d': r.returns_10d,
                'return_20d': r.returns_20d,
                'exit_price_5d': r.exit_price_5d,
                'exit_price_10d': r.exit_price_10d,
                'exit_price_20d': r.exit_price_20d,
                'exit_date_5d': r.exit_date_5d,
                'exit_date_10d': r.exit_date_10d,
                'exit_date_20d': r.exit_date_20d
            })

        df = pd.DataFrame(records)
        df = df.sort_values('signal_date').reset_index(drop=True)

        self.logger.info(f"回测完成，共 {len(df)} 个交易信号")

        return df

    def analyze_performance(self, df: pd.DataFrame) -> Dict:
        """
        分析回测绩效

        Returns:
            绩效统计字典
        """
        if df.empty:
            return {}

        stats = {}

        for period in [5, 10, 20]:
            col = f'return_{period}d'
            returns = df[col].dropna()

            if len(returns) == 0:
                continue

            stats[f'{period}d'] = {
                'count': len(returns),
                'mean': returns.mean(),
                'median': returns.median(),
                'std': returns.std(),
                'min': returns.min(),
                'max': returns.max(),
                'win_rate': (returns > 0).mean(),
                'profit_loss_ratio': abs(returns[returns > 0].mean() / returns[returns < 0].mean())
                                       if len(returns[returns < 0]) > 0 else float('inf')
            }

        return stats

    def print_report(self, df: pd.DataFrame, stats: Dict):
        """打印回测报告"""
        print("\n" + "="*80)
        print("妖股策略回测报告")
        print("="*80)

        print(f"\n回测区间: {df['signal_date'].min().strftime('%Y-%m-%d')} 至 "
              f"{df['signal_date'].max().strftime('%Y-%m-%d')}")
        print(f"信号总数: {len(df)}")
        print(f"成功买入: {len(df[df['days_delayed'] >= 0])} (延后买入也计入)")

        for period in [5, 10, 20]:
            if f'{period}d' not in stats:
                continue

            s = stats[f'{period}d']
            print(f"\n【持有{period}日收益统计】")
            print(f"  有效样本: {s['count']}")
            print(f"  平均收益: {s['mean']*100:.2f}%")
            print(f"  中位数收益: {s['median']*100:.2f}%")
            print(f"  胜率: {s['win_rate']*100:.1f}%")
            print(f"  最大收益: {s['max']*100:.2f}%")
            print(f"  最大亏损: {s['min']*100:.2f}%")
            print(f"  盈亏比: {s['profit_loss_ratio']:.2f}")

        # 显示最近信号
        print("\n【最近10个信号】")
        recent = df.tail(10)[['signal_date', 'stock_code', 'stock_name',
                              'score', 'buy_date', 'buy_price',
                              'return_5d', 'return_10d', 'return_20d']]
        print(recent.to_string(index=False))

        print("\n" + "="*80)

    def save_results(self, df: pd.DataFrame, output_file: str = 'backtest_results.csv'):
        """保存回测结果"""
        if not df.empty:
            # 格式化日期列
            date_cols = ['signal_date', 'buy_date', 'exit_date_5d',
                        'exit_date_10d', 'exit_date_20d']
            for col in date_cols:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None
                    )

            df.to_csv(output_file, index=False)
            self.logger.info(f"回测结果已保存: {output_file}")


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='妖股策略回测')
    parser.add_argument('--start', type=str, default='2020-01-01',
                       help='回测开始日期 (默认: 2020-01-01)')
    parser.add_argument('--end', type=str, default=None,
                       help='回测结束日期 (默认: 今天)')
    parser.add_argument('--min-score', type=float, default=80.0,
                       help='最小妖股评分 (默认: 80)')
    parser.add_argument('--lookback', type=int, default=60,
                       help='回看天数 (默认: 60)')
    parser.add_argument('--data-dir', type=str, default='./data/daily',
                       help='数据目录 (默认: ./data/daily)')
    parser.add_argument('--output', type=str, default='backtest_results.csv',
                       help='输出文件')
    parser.add_argument('--stocks', type=str, nargs='+', default=None,
                       help='指定股票代码列表')

    args = parser.parse_args()

    # 创建回测引擎
    engine = MonsterStockBacktest(
        data_dir=args.data_dir,
        lookback_days=args.lookback,
        min_score=args.min_score
    )

    # 运行回测
    results_df = engine.run_backtest(
        start_date=args.start,
        end_date=args.end,
        sample_stocks=args.stocks
    )

    if not results_df.empty:
        # 分析绩效
        stats = engine.analyze_performance(results_df)
        engine.print_report(results_df, stats)
        engine.save_results(results_df, args.output)
    else:
        print("未找到任何符合条件的交易信号")
        print("\n建议:")
        print("1. 确保数据目录中有足够的历史数据 (2020年至今)")
        print("2. 尝试降低 min-score 参数 (如 --min-score 70 或更低)")
        print("3. 检查数据日期范围: python -c \"import pandas as pd; df=pd.read_csv('data/daily/000001.csv'); print(df['date'].min(), df['date'].max())\"")

    return 0


if __name__ == '__main__':
    sys.exit(main())
