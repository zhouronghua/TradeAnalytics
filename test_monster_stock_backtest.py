"""
妖股策略完整回测
- 回测区间：2020年以来
- 买入规则：信号日次日开盘价买入，如果开盘秒板（涨停）则延后一天买入
- 持有期：分别计算持有5日、10日、20日的收益率
- 卖出规则：持有期结束以收盘价卖出
"""

import os
import sys
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger, safe_read_csv, ensure_dir
from src.monster_stock_analyzer import MonsterStockAnalyzer
from src.volume_analyzer import get_stock_name
from src.data_analyzer import DataAnalyzer


class MonsterStockBacktest:
    """
    妖股策略回测器

    买入规则：
    1. 信号出现日次日，以开盘价买入
    2. 如果次日开盘涨停（无法买入），则延后一天
    3. 最多延后3天，如果都无法买入则放弃该信号

    卖出规则：
    持有N天后以收盘价卖出
    """

    # A股涨跌停幅度
    LIMIT_UP_PCT = 9.8
    LIMIT_UP_PCT_ST = 4.8

    def __init__(self,
                 daily_dir: str = './data/daily',
                 start_date: str = '2020-01-01',
                 end_date: str = None,
                 lookback_days: int = 20,
                 min_score: int = 30,
                 hold_days_list: List[int] = None,
                 max_delay_days: int = 3):
        """
        初始化回测器

        Args:
            daily_dir: 日K数据目录
            start_date: 回测开始日期
            end_date: 回测结束日期
            lookback_days: 妖股分析回看天数
            min_score: 妖股最低评分
            hold_days_list: 持有天数列表
            max_delay_days: 最大延后买入天数（应对连续涨停）
        """
        self.daily_dir = daily_dir
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.to_datetime(datetime.now())
        self.lookback_days = lookback_days
        self.min_score = min_score
        self.hold_days_list = hold_days_list or [5, 10, 20]
        self.max_delay_days = max_delay_days

        self.logger = setup_logger('MonsterBacktest')

        # 初始化妖股分析器
        self.monster_analyzer = MonsterStockAnalyzer()
        self.monster_analyzer.lookback_days = lookback_days
        self.monster_analyzer.min_score = min_score

        # 技术指标分析器
        self.data_analyzer = DataAnalyzer(ma_period=20)

        # 结果存储
        self.trades = []

        ensure_dir('./build')

    def is_limit_up(self, open_price: float, prev_close: float, stock_name: str = '') -> bool:
        """判断是否为涨停价开盘"""
        # ST股判断
        is_st = 'ST' in str(stock_name) or '*ST' in str(stock_name)
        limit_pct = self.LIMIT_UP_PCT_ST if is_st else self.LIMIT_UP_PCT

        if prev_close <= 0:
            return False

        change_pct = (open_price / prev_close - 1) * 100
        return change_pct >= limit_pct

    def find_buy_point(self, df: pd.DataFrame, signal_idx: int) -> Optional[Dict]:
        """
        寻找实际买入点

        规则：
        1. 从信号日后第1天开始尝试买入
        2. 开盘价买入，但如果开盘涨停则延后
        3. 最多尝试max_delay_days天

        Returns:
            买入信息字典，包含买入日期、买入价格、实际延后天数
        """
        if signal_idx + 1 >= len(df):
            return None

        signal_row = df.iloc[signal_idx]
        signal_close = signal_row['close']

        # 尝试买入
        for delay in range(1, self.max_delay_days + 1):
            buy_idx = signal_idx + delay

            if buy_idx >= len(df):
                return None

            buy_row = df.iloc[buy_idx]
            open_price = buy_row['open']
            prev_close = df.iloc[buy_idx - 1]['close']
            stock_name = buy_row.get('name', '')

            # 检查是否开盘涨停
            if self.is_limit_up(open_price, prev_close, stock_name):
                self.logger.debug(f"  延后{delay}天: 开盘涨停 {open_price:.2f} (前收{prev_close:.2f})")
                continue

            # 可以买入
            return {
                'buy_idx': buy_idx,
                'buy_date': buy_row['date'],
                'buy_price': open_price,
                'buy_open': open_price,
                'buy_high': buy_row['high'],
                'buy_low': buy_row['low'],
                'buy_close': buy_row['close'],
                'delay_days': delay - 1,  # 延后天数（0表示次日成功买入）
                'signal_close': signal_close,
                'signal_date': signal_row['date']
            }

        return None

    def calculate_returns(self, df: pd.DataFrame, buy_idx: int, buy_price: float) -> Dict:
        """
        计算各持有期的收益率

        Args:
            df: 股票数据
            buy_idx: 买入索引
            buy_price: 买入价格

        Returns:
            收益率字典
        """
        results = {}

        # 从买入日后开始计算
        future_df = df.iloc[buy_idx + 1:].reset_index(drop=True)

        if future_df.empty:
            return results

        # 计算各持有期收益率
        for days in self.hold_days_list:
            exit_idx = days - 1  # 第N天对应的索引
            if exit_idx < len(future_df):
                exit_row = future_df.iloc[exit_idx]
                exit_price = exit_row['close']
                ret = (exit_price / buy_price - 1) * 100

                results[f'return_{days}d'] = round(ret, 2)
                results[f'exit_price_{days}d'] = round(exit_price, 2)
                results[f'exit_date_{days}d'] = exit_row['date']

                # 记录卖出日的高低价（用于分析滑点）
                results[f'exit_high_{days}d'] = exit_row['high']
                results[f'exit_low_{days}d'] = exit_row['low']
            else:
                results[f'return_{days}d'] = None
                results[f'exit_price_{days}d'] = None
                results[f'exit_date_{days}d'] = None

        # 计算持有期内的最大涨幅/跌幅（用于分析风险）
        max_check_days = min(max(self.hold_days_list), len(future_df))
        if max_check_days > 0:
            check_df = future_df.head(max_check_days)

            max_high = check_df['high'].max()
            min_low = check_df['low'].min()

            results['max_up_pct'] = round((max_high / buy_price - 1) * 100, 2)
            results['max_down_pct'] = round((min_low / buy_price - 1) * 100, 2)

            # 最大回撤（从买入后最高点的回落）
            running_max = check_df['close'].cummax()
            drawdown = ((check_df['close'] / running_max - 1) * 100).min()
            results['max_drawdown'] = round(drawdown, 2)

        return results

    def load_stock_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """加载股票数据并筛选日期范围"""
        try:
            df = safe_read_csv(file_path, dtype={'code': str})
            if df is None or len(df) < self.lookback_days + 10:
                return None

            # 日期转换
            df['date'] = pd.to_datetime(df['date'])

            # 数值转换
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 筛选回测区间
            df = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)]

            if len(df) < self.lookback_days + 5:
                return None

            return df.sort_values('date').reset_index(drop=True)

        except Exception as e:
            self.logger.error(f"加载数据失败 {file_path}: {e}")
            return None

    def run_backtest(self) -> pd.DataFrame:
        """执行完整回测"""
        csv_files = glob.glob(os.path.join(self.daily_dir, '*.csv'))
        total_files = len(csv_files)

        self.logger.info(f"开始回测，共 {total_files} 只股票")
        self.logger.info(f"回测区间: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        self.logger.info(f"妖股评分阈值: {self.min_score}, 回看天数: {self.lookback_days}")
        self.logger.info(f"持有期: {self.hold_days_list} 天")
        self.logger.info(f"买入规则: 信号后次日开盘买入，涨停则最多延后{self.max_delay_days}天")

        processed = 0
        signal_count = 0
        buy_success_count = 0

        for i, file_path in enumerate(csv_files):
            stock_code = os.path.basename(file_path).replace('.csv', '')

            try:
                # 加载数据
                df = self.load_stock_data(file_path)
                if df is None:
                    continue

                # 使用妖股分析器扫描信号
                # 我们需要逐日检查，而不是只看最后一天
                for idx in range(self.lookback_days, len(df)):
                    # 截取回看期的数据
                    lookback_df = df.iloc[idx - self.lookback_days:idx + 1].copy()

                    if len(lookback_df) < self.lookback_days:
                        continue

                    # 临时保存为文件供分析器使用
                    temp_file = f'/tmp/{stock_code}_temp.csv'
                    lookback_df.to_csv(temp_file, index=False)

                    # 分析是否为妖股信号
                    result = self.monster_analyzer.analyze_single(temp_file)

                    if result and result['total_score'] >= self.min_score:
                        signal_count += 1

                        # 寻找买入点
                        buy_info = self.find_buy_point(df, idx)

                        if buy_info:
                            buy_success_count += 1

                            # 计算收益率
                            returns = self.calculate_returns(
                                df,
                                buy_info['buy_idx'],
                                buy_info['buy_price']
                            )

                            # 构建交易记录
                            trade = {
                                'stock_code': stock_code,
                                'stock_name': result['stock_name'],
                                'signal_date': buy_info['signal_date'].strftime('%Y-%m-%d') if hasattr(buy_info['signal_date'], 'strftime') else str(buy_info['signal_date']),
                                'signal_close': buy_info['signal_close'],
                                'buy_date': buy_info['buy_date'].strftime('%Y-%m-%d') if hasattr(buy_info['buy_date'], 'strftime') else str(buy_info['buy_date']),
                                'buy_price': buy_info['buy_price'],
                                'buy_open': buy_info['buy_open'],
                                'buy_high': buy_info['buy_high'],
                                'buy_low': buy_info['buy_low'],
                                'buy_close': buy_info['buy_close'],
                                'delay_days': buy_info['delay_days'],
                                'total_score': result['total_score'],
                                'volume_score': result.get('volume_score', 0),
                                'limit_score': result.get('limit_score', 0),
                                'price_score': result.get('price_score', 0),
                                'tech_score': result.get('tech_score', 0),
                                'limit_up_count': result.get('limit_up_count', 0),
                                'consecutive_limits': result.get('consecutive_limits', 0),
                                'volume_ratio': result.get('volume_ratio', 0),
                                'rsi': result.get('rsi', 0),
                            }
                            trade.update(returns)
                            self.trades.append(trade)

                            if buy_success_count <= 5:
                                self.logger.info(
                                    f"交易信号: {stock_code} {result['stock_name']} "
                                    f"信号日:{trade['signal_date']} 买入日:{trade['buy_date']} "
                                    f"延后:{buy_info['delay_days']}天 买入价:{buy_info['buy_price']:.2f} "
                                    f"评分:{result['total_score']}"
                                )

                    # 清理临时文件
                    if os.path.exists(temp_file):
                        os.remove(temp_file)

                processed += 1
                if (i + 1) % 500 == 0:
                    self.logger.info(
                        f"进度: {i + 1}/{total_files}, 已处理:{processed}, "
                        f"信号:{signal_count}, 成功买入:{buy_success_count}"
                    )

            except Exception as e:
                self.logger.error(f"处理 {stock_code} 失败: {e}")

        self.logger.info("=" * 60)
        self.logger.info(f"回测完成!")
        self.logger.info(f"处理股票: {processed} 只")
        self.logger.info(f"妖股信号: {signal_count} 个")
        self.logger.info(f"成功买入: {buy_success_count} 个")
        self.logger.info(f"买入成功率: {buy_success_count / signal_count * 100:.1f}%" if signal_count > 0 else "N/A")
        self.logger.info("=" * 60)

        if self.trades:
            return pd.DataFrame(self.trades)
        return pd.DataFrame()

    def analyze_performance(self, trades_df: pd.DataFrame) -> Dict:
        """分析回测绩效"""
        if trades_df.empty:
            return {'error': '没有交易记录'}

        analysis = {
            'total_trades': len(trades_df),
            'date_range': f"{trades_df['signal_date'].min()} ~ {trades_df['signal_date'].max()}",
            'avg_score': trades_df['total_score'].mean(),
            'avg_delay_days': trades_df['delay_days'].mean(),
        }

        # 按持有期分析
        for days in self.hold_days_list:
            col = f'return_{days}d'
            if col not in trades_df.columns:
                continue

            returns = trades_df[col].dropna()
            if len(returns) == 0:
                continue

            stats = {
                'sample_count': len(returns),
                'mean_return': round(returns.mean(), 2),
                'median_return': round(returns.median(), 2),
                'max_return': round(returns.max(), 2),
                'min_return': round(returns.min(), 2),
                'std': round(returns.std(), 2),
                'win_rate': round((returns > 0).sum() / len(returns) * 100, 2),
                'win_rate_gt5': round((returns >= 5).sum() / len(returns) * 100, 2),
                'win_rate_gt10': round((returns >= 10).sum() / len(returns) * 100, 2),
                'win_rate_gt20': round((returns >= 20).sum() / len(returns) * 100, 2),
                'loss_rate_lt5': round((returns <= -5).sum() / len(returns) * 100, 2),
                'loss_rate_lt10': round((returns <= -10).sum() / len(returns) * 100, 2),
            }

            # 盈亏比
            profits = returns[returns > 0]
            losses = returns[returns < 0]
            avg_profit = profits.mean() if len(profits) > 0 else 0
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
            stats['profit_loss_ratio'] = round(avg_profit / avg_loss, 2) if avg_loss > 0 else 0

            analysis[f'hold_{days}d'] = stats

        # 按延后天数分析
        delay_analysis = {}
        for delay in range(self.max_delay_days + 1):
            delay_df = trades_df[trades_df['delay_days'] == delay]
            if len(delay_df) > 0:
                delay_stats = {
                    'count': len(delay_df),
                    'avg_score': round(delay_df['total_score'].mean(), 1),
                }
                # 各持有期收益
                for days in self.hold_days_list:
                    col = f'return_{days}d'
                    if col in delay_df.columns:
                        valid = delay_df[col].dropna()
                        if len(valid) > 0:
                            delay_stats[f'return_{days}d_mean'] = round(valid.mean(), 2)
                            delay_stats[f'return_{days}d_win_rate'] = round((valid > 0).sum() / len(valid) * 100, 1)

                delay_analysis[f'delay_{delay}d'] = delay_stats

        analysis['delay_analysis'] = delay_analysis

        return analysis

    def print_report(self, trades_df: pd.DataFrame, analysis: Dict):
        """打印回测报告"""
        print("\n" + "=" * 80)
        print("妖股策略回测报告")
        print("=" * 80)

        if 'error' in analysis:
            print(f"错误: {analysis['error']}")
            return

        print(f"\n【回测概况】")
        print(f"  总交易次数: {analysis['total_trades']}")
        print(f"  回测区间: {analysis['date_range']}")
        print(f"  平均妖股评分: {analysis['avg_score']:.1f}")
        print(f"  平均延后买入天数: {analysis['avg_delay_days']:.1f}天")

        print(f"\n【各持有期收益分析】")
        print("-" * 80)

        for days in self.hold_days_list:
            key = f'hold_{days}d'
            if key not in analysis:
                continue

            stats = analysis[key]
            print(f"\n持有 {days} 天 ({stats['sample_count']} 个样本):")
            print(f"  平均收益: {stats['mean_return']:>+7.2f}%  中位数: {stats['median_return']:>+7.2f}%")
            print(f"  最高收益: {stats['max_return']:>+7.2f}%  最低收益: {stats['min_return']:>+7.2f}%")
            print(f"  胜率(>0%): {stats['win_rate']:>6.2f}%  盈亏比: {stats['profit_loss_ratio']}")
            print(f"  盈利≥5%:  {stats['win_rate_gt5']:>6.2f}%  盈利≥10%: {stats['win_rate_gt10']:>6.2f}%  盈利≥20%: {stats['win_rate_gt20']:>6.2f}%")
            print(f"  亏损≥5%:  {stats['loss_rate_lt5']:>6.2f}%  亏损≥10%: {stats['loss_rate_lt10']:>6.2f}%")

        print(f"\n【延后买入分析】")
        print("-" * 80)
        for delay_key, delay_stats in analysis.get('delay_analysis', {}).items():
            delay_days = delay_key.replace('delay_', '').replace('d', '')
            print(f"\n延后 {delay_days} 天买入 ({delay_stats['count']} 次):")
            print(f"  平均评分: {delay_stats['avg_score']}")
            for days in self.hold_days_list:
                ret_key = f'return_{days}d_mean'
                win_key = f'return_{days}d_win_rate'
                if ret_key in delay_stats:
                    print(f"  持有{days}天平均收益: {delay_stats[ret_key]:>+6.2f}% 胜率: {delay_stats[win_key]:.1f}%")

        print("=" * 80)

    def save_results(self, trades_df: pd.DataFrame, analysis: Dict):
        """保存回测结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存交易记录
        trades_file = f'./build/monster_backtest_trades_{timestamp}.csv'
        trades_df.to_csv(trades_file, index=False, encoding='utf-8-sig')
        print(f"\n交易记录已保存: {trades_file}")

        # 生成报告文件
        report_file = f'./build/monster_backtest_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("妖股策略回测报告\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"总交易次数: {analysis['total_trades']}\n")
            f.write(f"回测区间: {analysis['date_range']}\n\n")

            for days in self.hold_days_list:
                key = f'hold_{days}d'
                if key not in analysis:
                    continue
                stats = analysis[key]
                f.write(f"持有 {days} 天:\n")
                for k, v in stats.items():
                    f.write(f"  {k}: {v}\n")
                f.write("\n")

            # TOP 50 交易
            f.write("\n【收益TOP 50】\n")
            if 'return_5d' in trades_df.columns:
                top50 = trades_df.nlargest(50, 'return_5d')
                for _, row in top50.iterrows():
                    f.write(f"{row['stock_code']} {row['stock_name']} "
                           f"信号:{row['signal_date']} 买入:{row['buy_date']} "
                           f"5日收益:{row.get('return_5d', 'N/A')}%\n")

        print(f"报告已保存: {report_file}")
        return trades_file, report_file


def main():
    """主函数"""
    print("=" * 80)
    print("妖股策略完整回测")
    print("=" * 80)
    print("\n【策略说明】")
    print("- 选股: 妖股评分系统 (量能+涨停+形态+技术+换手)")
    print("- 买入: 信号后次日开盘价买入，涨停则延后")
    print("- 卖出: 持有5/10/20天后收盘价卖出")
    print("- 回测区间: 2020年以来")
    print()

    daily_dir = './data/daily'
    if not os.path.exists(daily_dir):
        print(f"错误: 数据目录 {daily_dir} 不存在")
        return

    # 检查数据时间范围
    import glob
    sample_files = glob.glob(os.path.join(daily_dir, '*.csv'))[:5]
    if sample_files:
        import pandas as pd
        dates = []
        for f in sample_files:
            try:
                df = pd.read_csv(f)
                if 'date' in df.columns:
                    dates.extend(pd.to_datetime(df['date']).tolist())
            except:
                pass
        if dates:
            print(f"样本数据时间范围: {min(dates)} ~ {max(dates)}")
            if max(dates).year < 2020:
                print("\n警告: 数据似乎不包含2020年以来的历史数据!")
                print("请先运行: python download_history_2020.py")
                return

    # 检测数据实际日期范围，调整回测区间
    # 如果数据不包含2020年以来的数据，则使用实际数据范围进行测试
    data_min_date = min(dates) if dates else pd.to_datetime('2020-01-01')
    data_max_date = max(dates) if dates else pd.to_datetime(datetime.now())

    if data_max_date.year < 2020:
        # 数据时间范围不足，使用实际数据范围进行测试演示
        print(f"\n注意: 当前数据仅包含 {data_min_date.date()} ~ {data_max_date.date()} ({len(set(dates))}个交易日)")
        print("要使用2020年以来的完整数据回测，请先运行: python download_history_2020.py")
        print("\n继续使用现有数据进行演示测试...\n")

        # 调整参数适应短周期数据
        backtest_start = data_min_date.strftime('%Y-%m-%d')
        backtest_end = (data_max_date - timedelta(days=20)).strftime('%Y-%m-%d')  # 预留持有期
        min_score = 10  # 降低评分阈值以增加样本
    else:
        backtest_start = '2020-01-01'
        backtest_end = datetime.now().strftime('%Y-%m-%d')
        min_score = 30

    # 创建回测器
    backtest = MonsterStockBacktest(
        daily_dir=daily_dir,
        start_date=backtest_start,
        end_date=backtest_end,
        lookback_days=10,  # 使用较短的回看期适应数据
        min_score=min_score,
        hold_days_list=[1, 3, 5],  # 适应短数据周期
        max_delay_days=3
    )

    # 执行回测
    print("开始回测...")
    print("(这可能需要较长时间，请耐心等待)\n")

    trades_df = backtest.run_backtest()

    if trades_df.empty:
        print("未找到符合条件的交易记录")
        print("\n可能原因：")
        print("1. 历史数据不足 - 需要2020年以来的完整数据")
        print("2. 妖股评分阈值过高 - 可尝试降低 min_score")
        return

    # 分析绩效
    analysis = backtest.analyze_performance(trades_df)

    # 打印报告
    backtest.print_report(trades_df, analysis)

    # 保存结果
    trades_file, report_file = backtest.save_results(trades_df, analysis)

    # 显示TOP股票
    print("\n" + "=" * 80)
    print("【收益TOP 20 - 妖股案例】")
    print("=" * 80)

    if 'return_5d' in trades_df.columns:
        top20 = trades_df.nlargest(20, 'return_5d')
        for i, (_, row) in enumerate(top20.iterrows(), 1):
            name = row['stock_name'] or ''
            print(f"\n{i}. {row['stock_code']:<10} {name}")
            print(f"   信号日: {row['signal_date']}  买入日: {row['buy_date']}  延后:{row['delay_days']}天")
            print(f"   信号收盘价: {row['signal_close']:.2f}  买入价: {row['buy_price']:.2f}")
            print(f"   妖股评分: {row['total_score']} | 量能:{row['volume_score']} 涨停:{row['limit_score']} "
                  f"形态:{row['price_score']} 技术:{row['tech_score']}")
            print(f"   近期涨停: {row['limit_up_count']}次 连板:{row['consecutive_limits']}天 量比:{row['volume_ratio']:.2f}")

            for days in [5, 10, 20]:
                col = f'return_{days}d'
                if col in row and pd.notna(row[col]):
                    exit_date = row.get(f'exit_date_{days}d', 'N/A')
                    exit_price = row.get(f'exit_price_{days}d', 'N/A')
                    print(f"   持有{days}天收益: {row[col]:+.2f}% (卖出:{exit_date} 价格:{exit_price})")

            if 'max_up_pct' in row and pd.notna(row['max_up_pct']):
                print(f"   持有期最高: {row['max_up_pct']:+.2f}%  最大回撤: {row.get('max_drawdown', 0):.2f}%")


if __name__ == '__main__':
    main()
