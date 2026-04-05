"""
妖股发现策略回测测试
验证MonsterStockAnalyzer的选股能力在A股市场的表现

测试目标：
1. 识别出历史上哪些股票符合"妖股"特征
2. 记录妖股的买入点（符合条件的日期和价格）
3. 验证在买入点买入后，持有不同天数的收益率分布
4. 统计获利概率和获利比例
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


class MonsterStockBacktest:
    """妖股发现策略回测器"""

    def __init__(self,
                 daily_dir: str = './data/daily',
                 start_date: str = '2020-01-01',
                 end_date: str = None,
                 lookback_days: int = 20,
                 min_score: int = 30,
                 hold_days_list: List[int] = None):
        """
        初始化回测器

        Args:
            daily_dir: 日K数据目录
            start_date: 回测开始日期
            end_date: 回测结束日期
            lookback_days: 回看天数（用于妖股分析）
            min_score: 妖股最低评分
            hold_days_list: 测试的持有天数列表
        """
        self.daily_dir = daily_dir
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date) if end_date else pd.to_datetime(datetime.now())
        self.lookback_days = lookback_days
        self.min_score = min_score
        self.hold_days_list = hold_days_list or [1, 3, 5, 10, 20]

        self.logger = setup_logger('MonsterStockBacktest')
        self.analyzer = MonsterStockAnalyzer()
        self.analyzer.lookback_days = lookback_days
        self.analyzer.min_score = min_score

        # 存储结果
        self.detected_monsters = []  # 发现的妖股列表
        self.trades = []  # 交易记录

        ensure_dir('./build')

    def load_stock_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """加载单只股票数据"""
        try:
            df = safe_read_csv(file_path, dtype={'code': str})
            if df is None or len(df) < self.lookback_days + 5:
                return None

            # 转换日期和数值类型
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 筛选日期
            df = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)]

            if len(df) < self.lookback_days + 3:
                return None

            return df.sort_values('date').reset_index(drop=True)

        except Exception as e:
            return None

    def scan_for_monsters(self) -> pd.DataFrame:
        """
        扫描所有股票，找出符合条件的妖股候选

        Returns:
            妖股列表DataFrame
        """
        csv_files = glob.glob(os.path.join(self.daily_dir, '*.csv'))
        self.logger.info(f"开始扫描 {len(csv_files)} 只股票寻找妖股...")

        results = []
        processed = 0

        for file_path in csv_files:
            stock_code = os.path.basename(file_path).replace('.csv', '')

            try:
                result = self.analyzer.analyze_single(file_path)
                if result:
                    results.append(result)

                processed += 1
                if processed % 1000 == 0:
                    self.logger.info(f"已扫描 {processed}/{len(csv_files)} 只, 发现 {len(results)} 只妖股候选")

            except Exception as e:
                self.logger.error(f"分析 {stock_code} 失败: {e}")

        self.logger.info(f"扫描完成！发现 {len(results)} 只妖股候选")

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('total_score', ascending=False)
        self.detected_monsters = df
        return df

    def calculate_returns(self, stock_code: str, buy_date: datetime, buy_price: float) -> Dict:
        """
        计算买入后的收益率

        Args:
            stock_code: 股票代码
            buy_date: 买入日期
            buy_price: 买入价格

        Returns:
            收益率字典
        """
        file_path = os.path.join(self.daily_dir, f"{stock_code}.csv")
        df = self.load_stock_data(file_path)

        if df is None:
            return {}

        # 找到买入日期之后的数据
        future_data = df[df['date'] > buy_date]

        if future_data.empty:
            return {}

        results = {
            'buy_date': buy_date,
            'buy_price': buy_price,
            'stock_code': stock_code,
        }

        # 计算各持有期收益率
        for days in self.hold_days_list:
            if len(future_data) >= days:
                exit_price = future_data.iloc[days - 1]['close']
                ret = (exit_price / buy_price - 1) * 100
                results[f'return_{days}d'] = round(ret, 2)
                results[f'exit_price_{days}d'] = exit_price
            else:
                results[f'return_{days}d'] = None
                results[f'exit_price_{days}d'] = None

        # 计算持有期内的最高/最低价
        max_check_days = min(max(self.hold_days_list), len(future_data))
        if max_check_days > 0:
            check_data = future_data.head(max_check_days)
            high_price = check_data['high'].max()
            low_price = check_data['low'].min()
            results['max_up_pct'] = round((high_price / buy_price - 1) * 100, 2)
            results['max_down_pct'] = round((low_price / buy_price - 1) * 100, 2)

            # 最大回撤（从高点回落幅度）
            cummax = check_data['close'].cummax()
            drawdown = (check_data['close'] / cummax - 1).min()
            results['max_drawdown'] = round(drawdown * 100, 2)

        return results

    def run_backtest(self) -> pd.DataFrame:
        """执行完整回测"""
        # 第一步：扫描妖股
        monsters_df = self.scan_for_monsters()

        if monsters_df.empty:
            return pd.DataFrame()

        # 第二步：计算每只妖股的后续收益
        self.logger.info(f"开始计算 {len(monsters_df)} 只妖股的后续收益...")

        trades = []
        for idx, row in monsters_df.iterrows():
            stock_code = row['stock_code']
            buy_date = pd.to_datetime(row['date'])
            buy_price = row['close']

            # 计算收益率
            returns = self.calculate_returns(stock_code, buy_date, buy_price)

            if returns:
                # 合并妖股评分信息和收益信息
                combined = {
                    'stock_code': stock_code,
                    'stock_name': row['stock_name'],
                    'date': buy_date.strftime('%Y-%m-%d'),
                    'buy_price': buy_price,
                    'close': buy_price,
                    'change_pct': row['change_pct'],
                    'volume_ratio': row['volume_ratio'],
                    'total_score': row['total_score'],
                    'volume_score': row.get('volume_score', 0),
                    'limit_score': row.get('limit_score', 0),
                    'price_score': row.get('price_score', 0),
                    'tech_score': row.get('tech_score', 0),
                    'turnover_score': row.get('turnover_score', 0),
                    'limit_up_count': row.get('limit_up_count', 0),
                    'consecutive_limits': row.get('consecutive_limits', 0),
                    'rsi': row.get('rsi', 0),
                }
                combined.update(returns)
                trades.append(combined)

        self.trades = trades
        if trades:
            return pd.DataFrame(trades)
        return pd.DataFrame()

    def analyze_performance(self, trades_df: pd.DataFrame) -> Dict:
        """分析回测绩效"""
        if trades_df.empty:
            return {'error': '没有交易记录'}

        analysis = {}
        analysis['total_signals'] = len(trades_df)

        # 按持有天数分析
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
                'profit_rate_gt5': round((returns >= 5).sum() / len(returns) * 100, 2),  # 收益率>=5%
                'profit_rate_gt10': round((returns >= 10).sum() / len(returns) * 100, 2),  # 收益率>=10%
                'loss_rate_lt5': round((returns <= -5).sum() / len(returns) * 100, 2),  # 亏损>=5%
            }

            # 盈亏比
            profits = returns[returns > 0]
            losses = returns[returns < 0]
            avg_profit = profits.mean() if len(profits) > 0 else 0
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 1
            stats['profit_loss_ratio'] = round(avg_profit / avg_loss, 2) if avg_loss > 0 else 0

            analysis[f'hold_{days}d'] = stats

        return analysis

    def print_summary(self, trades_df: pd.DataFrame, analysis: Dict):
        """打印回测摘要"""
        print("\n" + "=" * 80)
        print("妖股发现策略回测报告")
        print("=" * 80)

        if 'error' in analysis:
            print(f"错误: {analysis['error']}")
            return

        print(f"\n【策略参数】")
        print(f"  妖股评分回看天数: {self.lookback_days}")
        print(f"  最低入选评分: {self.min_score}")
        print(f"  回测区间: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}")
        print(f"  发现妖股信号数: {analysis['total_signals']}")

        # 妖股特征分布
        print(f"\n【妖股特征分析】")
        avg_score = trades_df['total_score'].mean()
        print(f"  平均评分: {avg_score:.1f}")

        if 'consecutive_limits' in trades_df.columns:
            avg_consecutive = trades_df['consecutive_limits'].mean()
            max_consecutive = trades_df['consecutive_limits'].max()
            print(f"  平均连板天数: {avg_consecutive:.1f}  (最高: {max_consecutive}板)")

        if 'limit_up_count' in trades_df.columns:
            avg_limit = trades_df['limit_up_count'].mean()
            print(f"  平均近期涨停次数: {avg_limit:.1f}")

        # 各持有期表现
        print(f"\n【持有期收益率分析】")
        print("-" * 80)

        for days in self.hold_days_list:
            key = f'hold_{days}d'
            if key not in analysis:
                continue

            stats = analysis[key]
            sample = stats['sample_count']

            print(f"\n持有 {days} 天 ({sample} 个样本):")
            print(f"  平均收益: {stats['mean_return']:>6.2f}%   中位数: {stats['median_return']:>6.2f}%")
            print(f"  最大盈利: {stats['max_return']:>6.2f}%   最大亏损: {stats['min_return']:>6.2f}%")
            print(f"  胜率(>0%): {stats['win_rate']:>6.2f}%")
            print(f"  收益率>=5%概率: {stats['profit_rate_gt5']:>6.2f}%")
            print(f"  收益率>=10%概率: {stats['profit_rate_gt10']:>6.2f}%")
            print(f"  亏损>=5%概率: {stats['loss_rate_lt5']:>6.2f}%")
            print(f"  盈亏比: {stats['profit_loss_ratio']:>6.2f}")

        print("\n" + "=" * 80)

    def save_results(self, trades_df: pd.DataFrame, analysis: Dict):
        """保存回测结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存完整交易记录
        trades_file = f'./build/monster_stock_backtest_{timestamp}.csv'
        trades_df.to_csv(trades_file, index=False, encoding='utf-8-sig')
        self.logger.info(f"交易记录已保存: {trades_file}")

        # 保存妖股TOP列表
        top_file = f'./build/monster_stock_top_{timestamp}.csv'
        top_columns = ['stock_code', 'stock_name', 'date', 'buy_price',
                       'total_score', 'volume_score', 'limit_score',
                       'consecutive_limits', 'limit_up_count', 'volume_ratio']
        available_cols = [c for c in top_columns if c in trades_df.columns]
        trades_df[available_cols].head(50).to_csv(top_file, index=False, encoding='utf-8-sig')
        self.logger.info(f"妖股TOP50已保存: {top_file}")

        # 生成文本报告
        report_file = f'./build/monster_stock_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("妖股发现策略回测报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"【策略参数】\n")
            f.write(f"  妖股评分回看天数: {self.lookback_days}\n")
            f.write(f"  最低入选评分: {self.min_score}\n")
            f.write(f"  发现妖股信号数: {analysis['total_signals']}\n\n")

            f.write("【TOP 20 妖股】\n")
            f.write("-" * 80 + "\n")
            top20 = trades_df.head(20)
            for _, row in top20.iterrows():
                f.write(f"{row['stock_code']} {row['stock_name'] or ''} - "
                       f"日期:{row['date']} 评分:{row['total_score']} "
                       f"连板:{row.get('consecutive_limits', 0)} "
                       f"量比:{row.get('volume_ratio', 0):.2f}\n")

            f.write("\n")
            for days in self.hold_days_list:
                key = f'hold_{days}d'
                if key not in analysis:
                    continue
                stats = analysis[key]
                f.write(f"\n持有 {days} 天:\n")
                for k, v in stats.items():
                    f.write(f"  {k}: {v}\n")

        self.logger.info(f"报告已保存: {report_file}")

        return trades_file, report_file


def main():
    """主函数"""
    print("=" * 80)
    print("妖股发现策略回测测试")
    print("=" * 80)
    print("\n本测试将验证 MonsterStockAnalyzer 的妖股识别能力")
    print("以及在这些妖股信号买入后的收益率表现\n")

    # 检查数据
    daily_dir = './data/daily'
    if not os.path.exists(daily_dir):
        print(f"错误: 数据目录 {daily_dir} 不存在")
        return

    # 创建回测器 - 使用较低的评分阈值以便测试
    backtest = MonsterStockBacktest(
        daily_dir=daily_dir,
        start_date='2020-01-01',
        lookback_days=10,  # 降低回看天数
        min_score=10,  # 降低最低评分阈值
        hold_days_list=[1, 3, 5, 10, 20]
    )

    # 执行回测
    print("开始执行妖股扫描与回测...")
    print("(这可能需要几分钟时间)\n")

    trades_df = backtest.run_backtest()

    if trades_df.empty:
        print("未找到符合条件的妖股信号")
        print("\n可能原因：")
        print("1. 数据时间范围不足 - 需要更长的历史数据")
        print("2. 评分阈值过高 - 可以尝试降低 min_score")
        print("3. 数据量不足")
        return

    # 分析绩效
    analysis = backtest.analyze_performance(trades_df)

    # 打印摘要
    backtest.print_summary(trades_df, analysis)

    # 保存结果
    trades_file, report_file = backtest.save_results(trades_df, analysis)

    print(f"\n结果文件：")
    print(f"  完整记录: {trades_file}")
    print(f"  文本报告: {report_file}")

    # 展示TOP妖股
    print("\n" + "=" * 80)
    print("【TOP 15 妖股明细】")
    print("=" * 80)

    top15 = trades_df.head(15)
    for i, (_, row) in enumerate(top15.iterrows(), 1):
        name = row['stock_name'] or '未知'
        print(f"\n{i}. {row['stock_code']} {name}")
        print(f"   买入日期: {row['date']}  买入价: {row['buy_price']:.2f}")
        print(f"   综合评分: {row['total_score']} | "
              f"量能:{row.get('volume_score', 0)} | "
              f"涨停:{row.get('limit_score', 0)} | "
              f"形态:{row.get('price_score', 0)} | "
              f"技术:{row.get('tech_score', 0)}")
        print(f"   连板天数: {row.get('consecutive_limits', 0)} | "
              f"近期涨停: {row.get('limit_up_count', 0)} | "
              f"量比: {row.get('volume_ratio', 0):.2f} | "
              f"RSI: {row.get('rsi', 0):.1f}")

        # 显示收益率（如果有）
        ret_5d = row.get('return_5d')
        if pd.notna(ret_5d) and ret_5d is not None:
            print(f"   持有5日收益: {ret_5d:+.2f}%")
        ret_10d = row.get('return_10d')
        if pd.notna(ret_10d) and ret_10d is not None:
            print(f"   持有10日收益: {ret_10d:+.2f}%")

        max_up = row.get('max_up_pct')
        max_down = row.get('max_down_pct')
        if pd.notna(max_up) and pd.notna(max_down):
            print(f"   最大涨幅: {max_up:+.2f}%  最大跌幅: {max_down:+.2f}%")


if __name__ == '__main__':
    main()
