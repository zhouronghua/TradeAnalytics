"""
选股策略回测测试
验证放量+均线策略在2020年以来A股市场的表现

主要功能：
1. 按时间顺序逐日检查选股条件
2. 记录符合条件的买入点
3. 计算后续持有N天的收益率
4. 统计获利概率和收益分布
"""

import os
import sys
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger, safe_read_csv, ensure_dir
from src.data_analyzer import DataAnalyzer
from src.volume_analyzer import get_stock_name


class StrategyBacktest:
    """选股策略回测器"""

    def __init__(self,
                 daily_dir: str = './data/daily',
                 start_date: str = '2020-01-01',
                 end_date: str = None,
                 ma_period: int = 120,
                 volume_ratio_threshold: float = 5.0,
                 hold_days: int = 5):
        """
        初始化回测器

        Args:
            daily_dir: 日K数据目录
            start_date: 回测开始日期 'YYYY-MM-DD'
            end_date: 回测结束日期，默认到今天
            ma_period: 移动平均线周期
            volume_ratio_threshold: 成交量倍数阈值
            hold_days: 默认持有天数
        """
        self.daily_dir = daily_dir
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.to_datetime(datetime.now())
        self.ma_period = ma_period
        self.volume_ratio_threshold = volume_ratio_threshold
        self.hold_days = hold_days

        self.logger = setup_logger('StrategyBacktest')
        self.analyzer = DataAnalyzer(ma_period=ma_period)

        # 回测结果
        self.trades = []  # 所有交易记录
        self.signals = []  # 所有信号记录

        ensure_dir('./build')

    def load_all_stock_data(self) -> Dict[str, pd.DataFrame]:
        """加载所有股票的历史数据"""
        stock_data = {}
        csv_files = glob.glob(os.path.join(self.daily_dir, '*.csv'))

        self.logger.info(f"开始加载 {len(csv_files)} 只股票数据...")
        self.logger.info(f"要求MA周期: {self.ma_period}")

        skipped_count = 0
        for i, file_path in enumerate(csv_files):
            stock_code = os.path.basename(file_path).replace('.csv', '')
            try:
                df = safe_read_csv(file_path, dtype={'code': str})
                if df is None or len(df) < 10:  # 至少需要10条数据
                    skipped_count += 1
                    continue

                # 转换日期
                df['date'] = pd.to_datetime(df['date'])

                # 查看实际数据日期范围
                actual_start = df['date'].min()
                actual_end = df['date'].max()

                # 筛选日期范围
                df_filtered = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)]

                if len(df_filtered) < 10:
                    skipped_count += 1
                    if i == 0:  # 打印一个样本查看日期
                        self.logger.info(f"样本数据 {stock_code} 日期范围: {actual_start} ~ {actual_end}, 筛选后: {len(df_filtered)} 条")
                    continue

                df = df_filtered

                # 确保数值类型正确
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # 按日期排序
                df = df.sort_values('date').reset_index(drop=True)

                # 计算指标 - 使用实际可用数据长度调整MA周期
                effective_ma_period = min(self.ma_period, max(20, len(df) - 5))
                df = self.analyzer.analyze_stock(df, ma_period=effective_ma_period)

                if df is not None and len(df) > 0:
                    stock_data[stock_code] = df

                if (i + 1) % 1000 == 0:
                    self.logger.info(f"已处理 {i + 1}/{len(csv_files)} 只, 成功 {len(stock_data)} 只, 跳过 {skipped_count} 只")

            except Exception as e:
                self.logger.error(f"加载 {stock_code} 数据失败: {e}")

        self.logger.info(f"成功加载 {len(stock_data)} 只股票的回测数据, 跳过 {skipped_count} 只")
        return stock_data

    def check_buy_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, Optional[Dict]]:
        """
        检查特定日期是否符合买入条件

        条件：
        1. 成交量倍数 >= threshold
        2. 收盘价 >= MA均线

        Args:
            df: 股票数据DataFrame（已计算指标）
            idx: 当前检查的数据索引

        Returns:
            (是否触发信号, 信号详情)
        """
        if idx < 0 or idx >= len(df):
            return False, None

        ma_column = f'MA{self.ma_period}'
        required_cols = ['date', 'close', 'volume', ma_column, 'volume_ratio']

        if not all(col in df.columns for col in required_cols):
            return False, None

        row = df.iloc[idx]

        # 检查是否有足够的MA数据
        if pd.isna(row[ma_column]) or pd.isna(row['volume_ratio']):
            return False, None

        # 条件1：成交量倍数 >= 阈值
        volume_condition = row['volume_ratio'] >= self.volume_ratio_threshold

        # 条件2：收盘价 >= MA
        price_condition = row['close'] >= row[ma_column]

        if volume_condition and price_condition:
            signal = {
                'stock_code': '',  # 需要外部填充
                'date': row['date'],
                'buy_price': float(row['close']),
                'volume_ratio': float(row['volume_ratio']),
                'ma_value': float(row[ma_column]),
                'volume': float(row['volume']),
            }

            # 如果有前一日数据，计算前一日涨幅
            if idx >= 1:
                prev_close = df.iloc[idx - 1]['close']
                signal['prev_change_pct'] = (row['close'] / prev_close - 1) * 100
            else:
                signal['prev_change_pct'] = 0

            return True, signal

        return False, None

    def calculate_future_returns(self, df: pd.DataFrame, idx: int,
                                 hold_days_list: List[int] = None) -> Dict[str, float]:
        """
        计算买入后不同持有天数的收益率

        Args:
            df: 股票数据
            idx: 买入日期索引
            hold_days_list: 持有天数列表

        Returns:
            收益率字典 {'return_5d': 0.05, 'return_10d': 0.10, ...}
        """
        if hold_days_list is None:
            hold_days_list = [1, 3, 5, 10, 20, 30]

        buy_price = df.iloc[idx]['close']
        results = {}

        for days in hold_days_list:
            future_idx = idx + days
            if future_idx < len(df):
                future_price = df.iloc[future_idx]['close']
                ret = (future_price / buy_price - 1) * 100
                results[f'return_{days}d'] = round(ret, 2)
                results[f'exit_date_{days}d'] = df.iloc[future_idx]['date']
            else:
                results[f'return_{days}d'] = None
                results[f'exit_date_{days}d'] = None

        # 计算最大回撤和最高收益（持有期内）
        max_future_idx = min(idx + max(hold_days_list), len(df))
        if max_future_idx > idx + 1:
            price_slice = df.iloc[idx+1:max_future_idx]['close']
            high_price = price_slice.max()
            low_price = price_slice.min()

            results['max_up_pct'] = round((high_price / buy_price - 1) * 100, 2)
            results['max_down_pct'] = round((low_price / buy_price - 1) * 100, 2)

            # 止损点：买入后最低跌破-10%
            if results['max_down_pct'] <= -10:
                results['stop_loss_triggered'] = True
            else:
                results['stop_loss_triggered'] = False

        return results

    def run_backtest(self) -> pd.DataFrame:
        """
        执行完整回测

        Returns:
            交易记录DataFrame
        """
        stock_data = self.load_all_stock_data()

        if not stock_data:
            self.logger.error("没有加载到任何股票数据，无法执行回测")
            return pd.DataFrame()

        self.logger.info("开始执行回测...")

        total_signals = 0
        for stock_code, df in stock_data.items():
            # 从MA周期之后开始检查（确保MA有效）
            for idx in range(self.ma_period, len(df)):
                is_signal, signal = self.check_buy_signal(df, idx)

                if is_signal:
                    total_signals += 1
                    signal['stock_code'] = stock_code
                    signal['stock_name'] = get_stock_name(stock_code)

                    # 计算后续收益
                    returns = self.calculate_future_returns(df, idx)
                    signal.update(returns)

                    self.trades.append(signal.copy())

                    # 记录信号日志
                    self.logger.debug(
                        f"信号 {stock_code} {signal['date'].strftime('%Y-%m-%d')}: "
                        f"买入价={signal['buy_price']:.2f}, "
                        f"量比={signal['volume_ratio']:.2f}"
                    )

        self.logger.info(f"回测完成！共发现 {total_signals} 个买入信号")

        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            trades_df = trades_df.sort_values('date')
            return trades_df
        else:
            return pd.DataFrame()

    def analyze_results(self, trades_df: pd.DataFrame, 
                       profit_threshold: float = 0.0) -> Dict:
        """
        分析回测结果

        Args:
            trades_df: 交易记录
            profit_threshold: 盈利阈值(%)，默认0%即不亏就算盈利

        Returns:
            分析结果字典
        """
        if trades_df.empty:
            return {'error': '没有交易记录'}

        analysis = {}
        analysis['total_trades'] = len(trades_df)
        analysis['date_range'] = f"{trades_df['date'].min()} ~ {trades_df['date'].max()}"

        # 按持有天数分析
        hold_periods = [1, 3, 5, 10, 20]

        for days in hold_periods:
            col = f'return_{days}d'
            if col not in trades_df.columns:
                continue

            # 过滤有数据的记录
            valid_returns = trades_df[col].dropna()
            if len(valid_returns) == 0:
                continue

            period_analysis = {}
            period_analysis['sample_count'] = len(valid_returns)
            period_analysis['mean_return'] = round(valid_returns.mean(), 2)
            period_analysis['median_return'] = round(valid_returns.median(), 2)
            period_analysis['max_return'] = round(valid_returns.max(), 2)
            period_analysis['min_return'] = round(valid_returns.min(), 2)
            period_analysis['std'] = round(valid_returns.std(), 2)

            # 获利概率
            profit_count = (valid_returns > profit_threshold).sum()
            period_analysis['profit_probability'] = round(profit_count / len(valid_returns) * 100, 2)

            # 亏损概率
            loss_count = (valid_returns < 0).sum()
            period_analysis['loss_probability'] = round(loss_count / len(valid_returns) * 100, 2)

            # 盈亏比
            avg_profit = valid_returns[valid_returns > 0].mean() if (valid_returns > 0).any() else 0
            avg_loss = abs(valid_returns[valid_returns < 0].mean()) if (valid_returns < 0).any() else 1
            period_analysis['profit_loss_ratio'] = round(avg_profit / avg_loss, 2) if avg_loss > 0 else 0

            analysis[f'hold_{days}d'] = period_analysis

        # 分年度统计
        trades_df['year'] = pd.to_datetime(trades_df['date']).dt.year
        yearly_stats = []
        for year in sorted(trades_df['year'].unique()):
            year_df = trades_df[trades_df['year'] == year]
            year_stat = {
                'year': year,
                'trade_count': len(year_df),
                'avg_return_5d': round(year_df['return_5d'].mean(), 2) if 'return_5d' in year_df.columns else None,
                'profit_rate_5d': round((year_df['return_5d'] > 0).sum() / len(year_df) * 100, 2) if 'return_5d' in year_df.columns else None
            }
            yearly_stats.append(year_stat)
        analysis['yearly_stats'] = yearly_stats

        return analysis

    def save_results(self, trades_df: pd.DataFrame, analysis: Dict):
        """保存回测结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存交易记录
        trades_file = f'./build/backtest_trades_{timestamp}.csv'
        trades_df.to_csv(trades_file, index=False, encoding='utf-8-sig')
        self.logger.info(f"交易记录已保存: {trades_file}")

        # 生成报告
        report_file = f'./build/backtest_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("选股策略回测报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"策略说明：\n")
            f.write(f"- 买入条件：成交量倍数 >= {self.volume_ratio_threshold} 且 收盘价 >= MA{self.ma_period}\n")
            f.write(f"- 回测区间：{self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}\n")
            f.write(f"- 总交易次数：{analysis.get('total_trades', 0)}\n\n")

            f.write("-" * 60 + "\n")
            f.write("按持有周期分析\n")
            f.write("-" * 60 + "\n\n")

            for days in [1, 3, 5, 10, 20]:
                key = f'hold_{days}d'
                if key not in analysis:
                    continue

                stats = analysis[key]
                f.write(f"持有 {days} 天:\n")
                f.write(f"  样本数量: {stats['sample_count']}\n")
                f.write(f"  平均收益: {stats['mean_return']:.2f}%\n")
                f.write(f"  中位数收益: {stats['median_return']:.2f}%\n")
                f.write(f"  最大收益: {stats['max_return']:.2f}%\n")
                f.write(f"  最大亏损: {stats['min_return']:.2f}%\n")
                f.write(f"  收益标准差: {stats['std']:.2f}%\n")
                f.write(f"  获利概率: {stats['profit_probability']:.2f}%\n")
                f.write(f"  亏损概率: {stats['loss_probability']:.2f}%\n")
                f.write(f"  盈亏比: {stats['profit_loss_ratio']:.2f}\n\n")

            if 'yearly_stats' in analysis:
                f.write("-" * 60 + "\n")
                f.write("年度统计\n")
                f.write("-" * 60 + "\n\n")
                f.write(f"{'年份':<10}{'交易次数':<15}{'5日平均收益':<15}{'5日胜率':<10}\n")
                for stat in analysis['yearly_stats']:
                    f.write(f"{stat['year']:<10}{stat['trade_count']:<15}{str(stat['avg_return_5d']):<15}{str(stat['profit_rate_5d']):<10}\n")

        self.logger.info(f"回测报告已保存: {report_file}")
        return trades_file, report_file

    def print_summary(self, analysis: Dict):
        """打印回测结果摘要"""
        print("\n" + "=" * 70)
        print("选股策略回测结果")
        print("=" * 70)

        if 'error' in analysis:
            print(f"错误: {analysis['error']}")
            return

        print(f"\n策略条件：")
        print(f"  - 成交量倍数 >= {self.volume_ratio_threshold}")
        print(f"  - 收盘价 >= MA{self.ma_period}")
        print(f"  - 回测区间: {analysis.get('date_range', 'N/A')}")
        print(f"  - 总交易次数: {analysis.get('total_trades', 0)}")

        print("\n" + "-" * 70)
        print("按持有周期统计")
        print("-" * 70)

        for days in [1, 3, 5, 10, 20]:
            key = f'hold_{days}d'
            if key not in analysis:
                continue

            stats = analysis[key]
            sample_count = stats.get('sample_count', 0)
            if sample_count == 0:
                print(f"\n持有 {days} 天: 无有效数据")
                continue

            print(f"\n持有 {days} 天:")
            print(f"  样本数: {sample_count:>6}")
            print(f"  平均收益: {stats.get('mean_return', 0):>6.2f}%")
            print(f"  中位数: {stats.get('median_return', 0):>6.2f}%")
            print(f"  最大盈利: {stats.get('max_return', 0):>6.2f}%")
            print(f"  最大亏损: {stats.get('min_return', 0):>6.2f}%")
            print(f"  获利概率: {stats.get('profit_probability', 0):>6.2f}%")
            print(f"  亏损概率: {stats.get('loss_probability', 0):>6.2f}%")
            print(f"  盈亏比: {stats.get('profit_loss_ratio', 0):>6.2f}")

        if 'yearly_stats' in analysis:
            print("\n" + "-" * 70)
            print("年度统计")
            print("-" * 70)
            print(f"{'年份':<12}{'交易次数':<15}{'5日平均收益':<15}{'5日胜率':<10}")
            for stat in analysis['yearly_stats']:
                print(f"{stat['year']:<12}{stat['trade_count']:<15}{str(stat['avg_return_5d']):<15}{str(stat['profit_rate_5d']):<10}")

        print("=" * 70 + "\n")


def main():
    """主函数"""
    print("=" * 70)
    print("选股策略回测系统")
    print("=" * 70)

    # 检查数据目录
    daily_dir = './data/daily'
    if not os.path.exists(daily_dir):
        print(f"错误: 数据目录 {daily_dir} 不存在")
        return

    # 创建回测器 - 使用更灵活的参数适配现有数据
    backtest = StrategyBacktest(
        daily_dir=daily_dir,
        start_date='2020-01-01',
        ma_period=20,  # 使用MA20而不是MA120，因为数据时间范围有限
        volume_ratio_threshold=2.0,  # 降低阈值以便测试
        hold_days=5
    )

    # 执行回测
    print("\n开始执行回测，这可能需要几分钟时间...")
    trades_df = backtest.run_backtest()

    if trades_df.empty:
        print("未发现符合条件的买入信号")
        print("\n可能原因：")
        print("1. 数据不足 - 需要2020年以来的完整历史数据")
        print("2. 策略条件过于严格 - 可以尝试降低 volume_ratio_threshold")
        print("3. 数据格式问题")
        return

    # 分析结果
    analysis = backtest.analyze_results(trades_df)

    # 打印摘要
    backtest.print_summary(analysis)

    # 保存结果
    trades_file, report_file = backtest.save_results(trades_df, analysis)

    print(f"\n结果文件：")
    print(f"  交易记录: {trades_file}")
    print(f"  回测报告: {report_file}")

    # 展示部分妖股记录
    print("\n" + "-" * 70)
    print("买入信号列表 (按成交量倍数排序):")
    print("-" * 70)
    trades_sorted = trades_df.sort_values('volume_ratio', ascending=False)

    # 显示收益率最高的几笔交易（如果数据允许）
    for _, row in trades_sorted.head(20).iterrows():
        date_str = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], pd.Timestamp) else str(row['date'])
        ret_5d = row.get('return_5d', None)
        ret_10d = row.get('return_10d', None)

        ret_5d_str = f"{ret_5d:.2f}%" if pd.notna(ret_5d) and ret_5d is not None else "N/A"
        ret_10d_str = f"{ret_10d:.2f}%" if pd.notna(ret_10d) and ret_10d is not None else "N/A"

        print(f"  {row['stock_code']:<10} {row['stock_name'] or '':<10} {date_str} "
              f"买入价:{row['buy_price']:<8.2f} 量比:{row['volume_ratio']:<6.2f} "
              f"5日收益:{ret_5d_str:<10} 10日收益:{ret_10d_str}")


if __name__ == '__main__':
    main()
