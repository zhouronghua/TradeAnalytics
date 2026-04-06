#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
放量突破策略回测 - 基于2020年以来的完整历史数据

买入规则:
1. 信号日次日开盘价买入
2. 如果开盘涨停(秒板)，延后1天再试，最多延后3天
3. 持有期分别计算5日、10日、20日收益

选股信号:
- 量比 >= 2.0 (成交量是前5日均量的2倍以上)
- 当日涨幅 >= 3% (有价格突破)
- 收盘价站上MA20 (短期趋势向上)
- 近20日最大回撤 < 20% (排除连续暴跌后的反弹)
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.utils import setup_logger, safe_read_csv


@dataclass
class TradeSignal:
    """交易信号"""
    date: pd.Timestamp
    stock_code: str
    stock_name: str
    buy_price: float
    buy_date: pd.Timestamp
    volume_ratio: float
    change_pct: float
    close: float
    ma20: float


@dataclass
class TradeResult:
    """交易结果"""
    signal: TradeSignal
    actual_buy_price: float
    actual_buy_date: pd.Timestamp
    days_delayed: int
    returns_5d: Optional[float] = None
    returns_10d: Optional[float] = None
    returns_20d: Optional[float] = None


class VolumeBreakoutStrategy:
    """放量突破策略"""

    def __init__(self, data_dir: str = './data/daily',
                 volume_ratio_threshold: float = 2.0,
                 min_change_pct: float = 3.0,
                 max_drawdown_20d: float = 20.0):
        self.data_dir = data_dir
        self.volume_ratio_threshold = volume_ratio_threshold
        self.min_change_pct = min_change_pct
        self.max_drawdown_20d = max_drawdown_20d
        self.logger = setup_logger('VolumeBreakout')

    def load_stock_data(self, stock_code: str,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """加载股票数据"""
        file_path = os.path.join(self.data_dir, f"{stock_code}.csv")
        if not os.path.exists(file_path):
            return None

        df = safe_read_csv(file_path)
        if df is None or df.empty:
            return None

        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)

        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['close', 'volume'])
        if len(df) < 30:
            return None

        # 计算指标
        df['change_pct'] = df['close'].pct_change() * 100
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5']

        # 计算近20日最大回撤
        df['high_20d'] = df['high'].rolling(window=20).max()
        df['drawdown_20d'] = (df['close'] - df['high_20d']) / df['high_20d'] * 100

        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]

        return df if len(df) >= 10 else None

    def is_limit_up(self, open_price: float, prev_close: float) -> bool:
        """判断是否开盘涨停(涨幅>=9.5%)"""
        if prev_close <= 0:
            return False
        return (open_price - prev_close) / prev_close >= 0.095

    def find_buy_point(self, df: pd.DataFrame, signal_idx: int, max_delay: int = 3) -> Tuple[Optional[float], Optional[pd.Timestamp], int]:
        """寻找实际买入点"""
        signal_close = df.iloc[signal_idx]['close']

        for delay in range(max_delay + 1):
            buy_idx = signal_idx + 1 + delay
            if buy_idx >= len(df):
                return None, None, -1

            buy_date = df.iloc[buy_idx]['date']
            open_price = df.iloc[buy_idx]['open']

            if delay < max_delay and self.is_limit_up(open_price, signal_close):
                continue

            return open_price, buy_date, delay

        return None, None, -1

    def calculate_returns(self, df: pd.DataFrame, buy_idx: int, buy_price: float) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """计算持有期收益"""
        ret_5d = None
        ret_10d = None
        ret_20d = None

        if buy_idx + 5 < len(df):
            ret_5d = (df.iloc[buy_idx + 5]['close'] - buy_price) / buy_price
        if buy_idx + 10 < len(df):
            ret_10d = (df.iloc[buy_idx + 10]['close'] - buy_price) / buy_price
        if buy_idx + 20 < len(df):
            ret_20d = (df.iloc[buy_idx + 20]['close'] - buy_price) / buy_price

        return ret_5d, ret_10d, ret_20d

    def check_signal(self, df: pd.DataFrame, idx: int) -> bool:
        """检查是否产生买入信号"""
        if idx < 20:
            return False

        row = df.iloc[idx]

        # 基本条件
        if row['volume_ratio'] < self.volume_ratio_threshold:
            return False
        if row['change_pct'] < self.min_change_pct:
            return False
        if pd.isna(row['ma20']) or row['close'] <= row['ma20']:
            return False
        if pd.notna(row['drawdown_20d']) and row['drawdown_20d'] < -self.max_drawdown_20d:
            return False

        return True

    def analyze_single_stock(self, stock_code: str,
                            stock_name: str,
                            start_date: str,
                            end_date: str) -> List[TradeResult]:
        """分析单只股票"""
        results = []

        df = self.load_stock_data(stock_code, start_date, end_date)
        if df is None or len(df) < 25:
            return results

        # 遍历每一天检测信号
        for idx in range(20, len(df) - 20):
            if not self.check_signal(df, idx):
                continue

            row = df.iloc[idx]

            # 寻找买入点
            buy_price, buy_date, delay = self.find_buy_point(df, idx)
            if buy_price is None:
                continue

            buy_idx = df[df['date'] == buy_date].index[0]
            ret_5d, ret_10d, ret_20d = self.calculate_returns(df, buy_idx, buy_price)

            signal = TradeSignal(
                date=row['date'],
                stock_code=stock_code,
                stock_name=stock_name,
                buy_price=buy_price,
                buy_date=buy_date,
                volume_ratio=row['volume_ratio'],
                change_pct=row['change_pct'],
                close=row['close'],
                ma20=row['ma20']
            )

            result = TradeResult(
                signal=signal,
                actual_buy_price=buy_price,
                actual_buy_date=buy_date,
                days_delayed=delay,
                returns_5d=ret_5d,
                returns_10d=ret_10d,
                returns_20d=ret_20d
            )
            results.append(result)

        return results


def analyze_stock_worker(args):
    """多进程worker"""
    stock_code, stock_name, start_date, end_date, data_dir = args
    strategy = VolumeBreakoutStrategy(data_dir)
    return strategy.analyze_single_stock(stock_code, stock_name, start_date, end_date)


class VolumeBreakoutBacktest:
    """放量突破回测引擎"""

    def __init__(self, data_dir: str = './data/daily'):
        self.data_dir = data_dir
        self.logger = setup_logger('VolumeBreakoutBacktest')
        self.strategy = VolumeBreakoutStrategy(data_dir)

    def load_stock_list(self) -> pd.DataFrame:
        """加载股票列表"""
        stocks_file = os.path.join(os.path.dirname(self.data_dir), 'stocks', 'stock_list.csv')
        if os.path.exists(stocks_file):
            df = safe_read_csv(stocks_file, dtype={'code': str})
            if df is not None and not df.empty:
                return df

        codes = []
        for f in os.listdir(self.data_dir):
            if f.endswith('.csv'):
                codes.append(f.replace('.csv', ''))
        return pd.DataFrame({'code': codes, 'name': [''] * len(codes)})

    def run_backtest(self, start_date: str = '2020-01-01',
                    end_date: Optional[str] = None,
                    max_workers: int = 4) -> pd.DataFrame:
        """运行回测"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        self.logger.info(f"开始回测: {start_date} ~ {end_date}")
        self.logger.info(f"策略: 量比>={self.strategy.volume_ratio_threshold}, "
                        f"涨幅>={self.strategy.min_change_pct}%, 站稳MA20")

        stock_list = self.load_stock_list()
        if stock_list is None or stock_list.empty:
            self.logger.error("无法获取股票列表")
            return pd.DataFrame()

        total = len(stock_list)
        self.logger.info(f"共 {total} 只股票待分析")

        # 准备任务参数
        tasks = []
        for _, row in stock_list.iterrows():
            code = str(row['code'])
            name = row.get('name', '') if pd.notna(row.get('name', '')) else ''
            tasks.append((code, name, start_date, end_date, self.data_dir))

        all_results = []
        processed = 0

        # 多进程并行
        if max_workers > 1 and total > 100:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(analyze_stock_worker, task): task[0] for task in tasks}

                for future in as_completed(futures):
                    stock_code = futures[future]
                    processed += 1
                    try:
                        results = future.result(timeout=30)
                        all_results.extend(results)
                    except Exception as e:
                        self.logger.error(f"分析 {stock_code} 异常: {e}")

                    if processed % 500 == 0:
                        self.logger.info(f"进度: {processed}/{total}, 信号数: {len(all_results)}")
        else:
            # 单线程
            for task in tasks:
                stock_code = task[0]
                processed += 1
                results = analyze_stock_worker(task)
                all_results.extend(results)

                if processed % 500 == 0:
                    self.logger.info(f"进度: {processed}/{total}, 信号数: {len(all_results)}")

        self.logger.info(f"回测完成: 处理 {processed} 只股票, 发现 {len(all_results)} 个信号")

        if not all_results:
            return pd.DataFrame()

        # 转换为DataFrame
        records = []
        for r in all_results:
            records.append({
                'signal_date': r.signal.date,
                'stock_code': r.signal.stock_code,
                'stock_name': r.signal.stock_name,
                'volume_ratio': r.signal.volume_ratio,
                'change_pct': r.signal.change_pct,
                'close_price': r.signal.close,
                'ma20': r.signal.ma20,
                'buy_date': r.actual_buy_date,
                'buy_price': r.actual_buy_price,
                'days_delayed': r.days_delayed,
                'return_5d': r.returns_5d,
                'return_10d': r.returns_10d,
                'return_20d': r.returns_20d
            })

        df = pd.DataFrame(records)
        df = df.sort_values('signal_date').reset_index(drop=True)
        return df

    def analyze_performance(self, df: pd.DataFrame) -> Dict:
        """分析绩效"""
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
        """打印报告"""
        print("\n" + "="*80)
        print("放量突破策略回测报告")
        print("="*80)
        print(f"回测区间: {df['signal_date'].min().strftime('%Y-%m-%d')} ~ {df['signal_date'].max().strftime('%Y-%m-%d')}")
        print(f"信号总数: {len(df)}")
        print(f"成功买入: {len(df[df['days_delayed'] >= 0])}")

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

        # 年度统计
        df['year'] = df['signal_date'].dt.year
        yearly = df.groupby('year').agg({
            'signal_date': 'count',
            'return_5d': 'mean',
            'return_10d': 'mean',
            'return_20d': 'mean'
        }).round(4)
        yearly.columns = ['信号数', '5日平均收益', '10日平均收益', '20日平均收益']
        print(f"\n【年度统计】")
        print(yearly.to_string())

        # 最近信号
        print(f"\n【最近20个信号】")
        recent = df.tail(20)[['signal_date', 'stock_code', 'stock_name',
                            'volume_ratio', 'change_pct', 'buy_price',
                            'return_5d', 'return_10d', 'return_20d']]
        print(recent.to_string(index=False))

        print("\n" + "="*80)

    def save_results(self, df: pd.DataFrame, output_file: str = 'volume_breakout_results.csv'):
        """保存结果"""
        if not df.empty:
            for col in ['signal_date', 'buy_date']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None)
            df.to_csv(output_file, index=False)
            self.logger.info(f"结果已保存: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='放量突破策略回测')
    parser.add_argument('--start', default='2020-01-01', help='回测开始日期')
    parser.add_argument('--end', default=None, help='回测结束日期')
    parser.add_argument('--data-dir', default='./data/daily', help='数据目录')
    parser.add_argument('--output', default='volume_breakout_results.csv', help='输出文件')
    parser.add_argument('--workers', type=int, default=4, help='并行进程数')
    parser.add_argument('--volume-ratio', type=float, default=2.0, help='量比阈值')
    parser.add_argument('--min-change', type=float, default=3.0, help='最小涨幅(%)')
    args = parser.parse_args()

    engine = VolumeBreakoutBacktest(args.data_dir)
    engine.strategy.volume_ratio_threshold = args.volume_ratio
    engine.strategy.min_change_pct = args.min_change

    df = engine.run_backtest(args.start, args.end, max_workers=args.workers)

    if not df.empty:
        stats = engine.analyze_performance(df)
        engine.print_report(df, stats)
        engine.save_results(df, args.output)
    else:
        print("未找到符合条件的交易信号")
        print("建议: 降低量比阈值或最小涨幅要求")

    return 0


if __name__ == '__main__':
    sys.exit(main())
