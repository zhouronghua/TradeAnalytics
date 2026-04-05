"""
放量突破策略回测测试
验证成交量放量+价格突破策略在A股市场的表现

测试目标：
1. 识别放量突破的股票（成交量暴增 + 价格站上均线）
2. 记录买入点和具体价格
3. 验证买入后持有不同天数的收益率分布
4. 统计获利概率、盈亏比、最大回撤等指标

策略条件：
- 成交量倍数 >= 2.0（当日成交量 / 前日成交量）
- 收盘价 >= MA20
- 可选：当日涨幅 > 3%（强势突破）
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


class VolumeBreakoutBacktest:
    """放量突破策略回测器"""

    def __init__(self,
                 daily_dir: str = './data/daily',
                 start_date: str = '2020-01-01',
                 end_date: str = None,
                 ma_period: int = 20,
                 volume_ratio_threshold: float = 2.0,
                 min_price_change: float = None,
                 hold_days_list: List[int] = None):
        """
        初始化回测器

        Args:
            daily_dir: 日K数据目录
            start_date: 回测开始日期
            end_date: 回测结束日期
            ma_period: 移动平均线周期
            volume_ratio_threshold: 成交量倍数阈值
            min_price_change: 最小当日涨幅要求(%)，None表示无要求
            hold_days_list: 测试的持有天数列表
        """
        self.daily_dir = daily_dir
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.to_datetime(datetime.now())
        self.ma_period = ma_period
        self.volume_ratio_threshold = volume_ratio_threshold
        self.min_price_change = min_price_change
        self.hold_days_list = hold_days_list or [1, 3, 5, 10, 20]

        self.logger = setup_logger('VolumeBreakoutBacktest')
        self.analyzer = DataAnalyzer(ma_period=ma_period)

        # 结果存储
        self.trades = []

        ensure_dir('./build')

    def load_stock_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """加载单只股票数据"""
        try:
            df = safe_read_csv(file_path)
            if df is None or len(df) < 10:
                return None

            # 转换日期
            df['date'] = pd.to_datetime(df['date'])

            # 数值转换
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 筛选日期
            df = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)]

            if len(df) < 10:
                return None

            df = df.sort_values('date').reset_index(drop=True)

            # 计算指标 - 根据数据长度动态调整MA周期
            # 至少需要5天数据来计算MA
            if len(df) < 5:
                return None

            # 使用较短的MA周期或实际可用的周期
            effective_ma = min(self.ma_period, max(5, len(df) - 2))
            df = self.analyzer.analyze_stock(df, ma_period=effective_ma)

            # 重命名MA列以匹配策略配置
            if effective_ma != self.ma_period:
                # 如果使用了不同的MA周期，需要重命名列
                old_ma_col = f'MA{effective_ma}'
                new_ma_col = f'MA{self.ma_period}'
                if old_ma_col in df.columns and new_ma_col not in df.columns:
                    df[new_ma_col] = df[old_ma_col]

            return df

        except Exception as e:
            return None

    def check_buy_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, Optional[Dict]]:
        """检查买入信号"""
        if idx < 1 or idx >= len(df):
            return False, None

        ma_column = f'MA{self.ma_period}'
        if ma_column not in df.columns:
            return False, None

        row = df.iloc[idx]
        prev_row = df.iloc[idx - 1]

        # 检查NaN
        if pd.isna(row['volume_ratio']) or pd.isna(row[ma_column]):
            return False, None

        # 条件1：成交量倍数 >= 阈值
        volume_ok = row['volume_ratio'] >= self.volume_ratio_threshold

        # 条件2：收盘价 >= MA
        price_ok = row['close'] >= row[ma_column]

        # 条件3：当日涨幅（如果有要求）
        change_ok = True
        if self.min_price_change is not None:
            if 'change_pct' in df.columns:
                change_ok = row['change_pct'] >= self.min_price_change
            else:
                # 计算当日涨幅
                change_pct = (row['close'] / prev_row['close'] - 1) * 100
                change_ok = change_pct >= self.min_price_change

        if volume_ok and price_ok and change_ok:
            signal = {
                'stock_code': '',
                'date': row['date'],
                'buy_price': float(row['close']),
                'volume': float(row['volume']),
                'volume_ratio': float(row['volume_ratio']),
                'ma_value': float(row[ma_column]),
                'prev_close': float(prev_row['close']),
            }

            # 计算当日涨幅
            change_pct = (row['close'] / prev_row['close'] - 1) * 100
            signal['day_change_pct'] = round(change_pct, 2)

            # 补充其他价格信息
            signal['open'] = float(row.get('open', row['close']))
            signal['high'] = float(row.get('high', row['close']))
            signal['low'] = float(row.get('low', row['close']))

            return True, signal

        return False, None

    def calculate_returns(self, df: pd.DataFrame, signal_idx: int) -> Dict:
        """
        计算后续收益率

        买入规则：信号出现后，隔天以最高价作为实际买入价（模拟追高涨停价买入）
        """
        results = {}

        # 信号日数据
        signal_row = df.iloc[signal_idx]
        signal_date = signal_row['date']
        signal_close = signal_row['close']

        # 获取信号日后的数据（从第二天开始）
        if signal_idx + 1 >= len(df):
            return results  # 没有后续数据

        future_df = df.iloc[signal_idx+1:].reset_index(drop=True)

        if future_df.empty:
            return results

        # 买入价：信号日次日的最高价（模拟追高买入）
        buy_price = future_df.iloc[0]['high']
        buy_date = future_df.iloc[0]['date']

        results['actual_buy_price'] = round(buy_price, 2)
        results['actual_buy_date'] = buy_date
        results['signal_close'] = round(signal_close, 2)
        results['buy_premium'] = round((buy_price / signal_close - 1) * 100, 2)  # 买入溢价

        # 各持有期收益率（从实际买入后计算）
        hold_start_idx = 0  # future_df中的起始索引

        for days in self.hold_days_list:
            exit_idx = hold_start_idx + days - 1  # 持有N天后的索引
            if exit_idx < len(future_df):
                exit_price = future_df.iloc[exit_idx]['close']
                ret = (exit_price / buy_price - 1) * 100
                results[f'return_{days}d'] = round(ret, 2)
                results[f'exit_price_{days}d'] = round(exit_price, 2)
                results[f'exit_date_{days}d'] = future_df.iloc[exit_idx]['date']
            else:
                results[f'return_{days}d'] = None
                results[f'exit_price_{days}d'] = None
                results[f'exit_date_{days}d'] = None

        # 最大涨幅/跌幅（从买入后持有期内）
        max_check_days = min(max(self.hold_days_list), len(future_df))
        if max_check_days > 0:
            check_df = future_df.head(max_check_days)
            max_high = check_df['high'].max()
            min_low = check_df['low'].min()

            results['max_up_pct'] = round((max_high / buy_price - 1) * 100, 2)
            results['max_down_pct'] = round((min_low / buy_price - 1) * 100, 2)

        return results

    def run_backtest(self) -> pd.DataFrame:
        """执行完整回测"""
        csv_files = glob.glob(os.path.join(self.daily_dir, '*.csv'))
        self.logger.info(f"开始回测 {len(csv_files)} 只股票...")
        self.logger.info(f"策略条件: 成交量倍数>={self.volume_ratio_threshold}, MA{self.ma_period}")

        total_signals = 0

        for i, file_path in enumerate(csv_files):
            stock_code = os.path.basename(file_path).replace('.csv', '')

            df = self.load_stock_data(file_path)
            if df is None:
                continue

            # 从第1行开始检查（需要前一日数据计算volume_ratio）
            for idx in range(1, len(df)):
                is_signal, signal = self.check_buy_signal(df, idx)

                if is_signal:
                    total_signals += 1
                    signal['stock_code'] = stock_code
                    signal['stock_name'] = get_stock_name(stock_code)

                    # 计算后续收益（按新规则：次日最高价买入）
                    returns = self.calculate_returns(df, idx)
                    signal.update(returns)

                    # 更新买入价为实际买入价（如果有的话）
                    if 'actual_buy_price' in returns:
                        signal['original_signal_price'] = signal['buy_price']  # 保存原始信号价格
                        signal['buy_price'] = returns['actual_buy_price']      # 更新为实际买入价
                        signal['buy_date'] = returns['actual_buy_date']

                    self.trades.append(signal)
                    # 调试日志
                    if total_signals <= 5:
                        bp = signal.get('buy_price', 0)
                        pr = signal.get('buy_premium', 0)
                        self.logger.info(f"发现信号: {stock_code} 信号日={signal['date']} 量比={signal['volume_ratio']:.2f} "
                                        f"实际买入={bp:.2f} 溢价={pr:.2f}%")

            if (i + 1) % 1000 == 0:
                self.logger.info(f"已处理 {i+1}/{len(csv_files)}, 发现 {total_signals} 个信号")

        self.logger.info(f"回测完成！共发现 {total_signals} 个买入信号")

        if self.trades:
            return pd.DataFrame(self.trades)
        return pd.DataFrame()

    def analyze_performance(self, trades_df: pd.DataFrame) -> Dict:
        """分析绩效"""
        if trades_df.empty:
            return {'error': '没有交易记录'}

        analysis = {
            'total_signals': len(trades_df),
            'date_range': f"{trades_df['date'].min()} ~ {trades_df['date'].max()}",
            'avg_volume_ratio': trades_df['volume_ratio'].mean(),
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
                'loss_rate_lt5': round((returns <= -5).sum() / len(returns) * 100, 2),
            }

            # 盈亏比
            profits = returns[returns > 0]
            losses = returns[returns < 0]
            avg_profit = profits.mean() if len(profits) > 0 else 0
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
            stats['profit_loss_ratio'] = round(avg_profit / avg_loss, 2) if avg_loss > 0 else 0

            analysis[f'hold_{days}d'] = stats

        # 分析最大涨幅/跌幅分布
        if 'max_up_pct' in trades_df.columns:
            analysis['max_up_stats'] = {
                'mean': round(trades_df['max_up_pct'].mean(), 2),
                'max': round(trades_df['max_up_pct'].max(), 2),
            }
        if 'max_down_pct' in trades_df.columns:
            analysis['max_down_stats'] = {
                'mean': round(trades_df['max_down_pct'].mean(), 2),
                'min': round(trades_df['max_down_pct'].min(), 2),
            }

        return analysis

    def print_report(self, trades_df: pd.DataFrame, analysis: Dict):
        """打印回测报告"""
        print("\n" + "=" * 80)
        print("放量突破策略回测报告")
        print("=" * 80)

        if 'error' in analysis:
            print(f"错误: {analysis['error']}")
            return

        print(f"\n【策略条件】")
        print(f"  成交量倍数 >= {self.volume_ratio_threshold}")
        print(f"  收盘价 >= MA{self.ma_period}")
        if self.min_price_change:
            print(f"  当日涨幅 >= {self.min_price_change}%")
        print(f"  回测区间: {analysis['date_range']}")
        print(f"  总信号数: {analysis['total_signals']}")
        print(f"  平均成交量倍数: {analysis['avg_volume_ratio']:.2f}")

        print(f"\n【持有期收益分析】")
        print("-" * 80)

        # 显示买入溢价统计
        if 'buy_premium' in trades_df.columns:
            valid_premium = trades_df['buy_premium'].dropna()
            if len(valid_premium) > 0:
                print(f"\n【买入溢价统计】(信号日收盘价→次日最高价买入)")
                print(f"  平均溢价: {valid_premium.mean():>+6.2f}%")
                print(f"  最大溢价: {valid_premium.max():>+6.2f}%")
                print(f"  最小溢价: {valid_premium.min():>+6.2f}%")

        for days in self.hold_days_list:
            key = f'hold_{days}d'
            if key not in analysis:
                continue

            stats = analysis[key]
            print(f"\n持有 {days} 天 (样本: {stats['sample_count']}):")
            print(f"  平均收益: {stats['mean_return']:>+7.2f}%  中位数: {stats['median_return']:>+7.2f}%")
            print(f"  最高收益: {stats['max_return']:>+7.2f}%  最低收益: {stats['min_return']:>+7.2f}%")
            print(f"  胜率(>0%): {stats['win_rate']:>6.2f}%  盈亏比: {stats['profit_loss_ratio']}")
            print(f"  盈利>=5%: {stats['win_rate_gt5']:>6.2f}%  盈利>=10%: {stats['win_rate_gt10']:>6.2f}%")
            print(f"  亏损>=5%: {stats['loss_rate_lt5']:>6.2f}%")

        if 'max_up_stats' in analysis:
            print(f"\n【持有期最大波动】")
            print(f"  平均最大涨幅: {analysis['max_up_stats']['mean']:.2f}%")
            print(f"  最高涨幅记录: {analysis['max_up_stats']['max']:.2f}%")
        if 'max_down_stats' in analysis:
            print(f"  平均最大跌幅: {analysis['max_down_stats']['mean']:.2f}%")
            print(f"  最大跌幅记录: {analysis['max_down_stats']['min']:.2f}%")

        print("=" * 80)

    def save_results(self, trades_df: pd.DataFrame, analysis: Dict):
        """保存结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存交易记录
        trades_file = f'./build/volume_breakout_trades_{timestamp}.csv'
        trades_df.to_csv(trades_file, index=False, encoding='utf-8-sig')
        print(f"\n交易记录已保存: {trades_file}")

        # 生成报告文件
        report_file = f'./build/volume_breakout_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("放量突破策略回测报告\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"策略条件: 成交量倍数>={self.volume_ratio_threshold}, MA{self.ma_period}\n")
            f.write(f"信号总数: {analysis['total_signals']}\n\n")

            for days in self.hold_days_list:
                key = f'hold_{days}d'
                if key not in analysis:
                    continue
                stats = analysis[key]
                f.write(f"持有 {days} 天:\n")
                for k, v in stats.items():
                    f.write(f"  {k}: {v}\n")
                f.write("\n")

            # 写入TOP 30交易
            f.write("\n【TOP 30 按收益率排序】\n")
            f.write("-" * 80 + "\n")

            if 'return_5d' in trades_df.columns:
                top30 = trades_df.nlargest(30, 'return_5d')
                for _, row in top30.iterrows():
                    f.write(f"{row['stock_code']} {row['date']} - 5日收益: {row.get('return_5d', 'N/A')}%\n")

        print(f"文本报告已保存: {report_file}")
        return trades_file, report_file


def main():
    """主函数"""
    print("=" * 80)
    print("放量突破策略回测测试")
    print("=" * 80)
    print("\n策略: 成交量放量 + 价格站上均线")
    print("目标: 发现潜在妖股，验证买入点，统计后续收益\n")

    daily_dir = './data/daily'
    if not os.path.exists(daily_dir):
        print(f"错误: 数据目录 {daily_dir} 不存在")
        return

    # 创建回测器 - 从1个月前开始回测
    # 计算日期：结束日期为数据最后一天前5天（确保能计算5日收益）
    # 开始日期为1个月前
    end_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=35)).strftime('%Y-%m-%d')  # 约1个月前

    print(f"回测区间: {start_date} ~ {end_date} (约1个月)")

    backtest = VolumeBreakoutBacktest(
        daily_dir=daily_dir,
        start_date=start_date,
        end_date=end_date,
        ma_period=20,
        volume_ratio_threshold=2.0,
        hold_days_list=[1, 3, 5, 10, 20]
    )

    # 执行回测
    print("开始回测...")
    trades_df = backtest.run_backtest()

    if trades_df.empty:
        print("未发现符合条件的买入信号")
        return

    # 分析绩效
    analysis = backtest.analyze_performance(trades_df)

    # 打印报告
    backtest.print_report(trades_df, analysis)

    # 保存结果
    trades_file, report_file = backtest.save_results(trades_df, analysis)

    # 显示TOP股票
    print("\n" + "=" * 80)
    print("【买入信号明细 TOP 20】")
    print("=" * 80)

    # 格式化日期辅助函数
    def fmt_date(d):
        if pd.isna(d):
            return 'N/A'
        if hasattr(d, 'strftime'):
            return d.strftime('%Y-%m-%d')
        return str(d)

    top20 = trades_df.sort_values('volume_ratio', ascending=False).head(20)
    for i, (_, row) in enumerate(top20.iterrows(), 1):
        name = row['stock_name'] or '未知'
        signal_date = fmt_date(row['date'])
        buy_date = row.get('buy_date', row['date'])

        # 获取价格信息
        signal_price = row.get('original_signal_price', row['buy_price'])  # 如果没有就是实际买入价
        actual_buy = row['buy_price']
        premium = row.get('buy_premium', 0)

        print(f"\n{i}. {row['stock_code']:<10} {name}")
        print(f"   信号日期: {signal_date}  实际买入日: {fmt_date(buy_date)}")
        print(f"   信号收盘价: {signal_price:.2f}  实际买入价: {actual_buy:.2f}  买入溢价: {premium:+.2f}%")
        print(f"   当日涨幅: {row['day_change_pct']:+.2f}%  量比: {row['volume_ratio']:.2f}")

        # 显示收益
        for days in [1, 3, 5]:
            col = f'return_{days}d'
            if col in row and pd.notna(row[col]):
                exit_date = row.get(f'exit_date_{days}d', 'N/A')
                print(f"   持有{days}日收益: {row[col]:+.2f}% (卖出日: {fmt_date(exit_date)})")

        if 'max_up_pct' in row and pd.notna(row['max_up_pct']):
            print(f"   持有期最高: {row['max_up_pct']:+.2f}%  最低: {row['max_down_pct']:+.2f}%")

    # 统计高收益股票
    if 'return_5d' in trades_df.columns:
        print("\n" + "=" * 80)
        print("【5日收益TOP 10 (获利妖股)】")
        print("=" * 80)

        top_profit = trades_df.nlargest(10, 'return_5d')
        for _, row in top_profit.iterrows():
            name = row['stock_name'] or ''
            date_str = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], pd.Timestamp) else str(row['date'])
            print(f"  {row['stock_code']:<10} {name:<8} {date_str}  "
                  f"买入:{row['buy_price']:<8.2f}  5日收益:{row['return_5d']:>+7.2f}%  "
                  f"量比:{row['volume_ratio']:.2f}  当日涨幅:{row['day_change_pct']:+.2f}%")


if __name__ == '__main__':
    main()
