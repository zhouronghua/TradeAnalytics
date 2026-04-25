#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股策略回测脚本

回测逻辑：
1. 读取历史选股结果（monster_stock_*.csv）
2. 对于每只股票，确定买入日期（选股后第一个非秒板交易日）
3. 计算持有5天、10天、20天的收益率
4. 统计胜率和平均收益

买入规则：
- 选股后下一个交易日开盘价买入
- 如果当天秒板（开盘价涨幅>=9.8%），则延后一天，直到非秒板日买入

卖出规则：
- 持有5天/10天/20天后收盘价卖出
"""

import os
import sys
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.utils import setup_logger, safe_read_csv


class StrategyBacktest:
    """选股策略回测器"""

    # 涨停判定阈值
    LIMIT_UP_PCT = 9.8
    LIMIT_UP_PCT_ST = 4.8

    # 持有天数选项
    HOLD_DAYS = [5, 10, 20]

    def __init__(self, daily_dir: str = 'data/daily', results_dir: str = 'data/results'):
        self.logger = setup_logger('StrategyBacktest')
        self.daily_dir = daily_dir
        self.results_dir = results_dir

    def parse_result_date(self, filename: str) -> Optional[str]:
        """
        从结果文件名解析日期
        格式: monster_stock_YYYYMMDD_HHMMSS.csv
        """
        match = re.search(r'monster_stock_(\d{8})_', filename)
        if match:
            return match.group(1)
        return None

    def get_next_trading_date(self, date_str: str) -> str:
        """
        获取下一个交易日（简单实现，跳过周末）
        """
        date = datetime.strptime(date_str, '%Y%m%d')
        next_date = date + timedelta(days=1)

        # 跳过周末
        while next_date.weekday() >= 5:  # 5=周六, 6=周日
            next_date += timedelta(days=1)

        return next_date.strftime('%Y-%m-%d')

    def is_limit_up_open(self, open_price: float, prev_close: float, is_st: bool = False) -> bool:
        """
        判断是否秒板（开盘涨停）
        """
        if prev_close <= 0:
            return False

        pct_change = (open_price - prev_close) / prev_close * 100
        threshold = self.LIMIT_UP_PCT_ST if is_st else self.LIMIT_UP_PCT

        return pct_change >= threshold

    def find_buy_date(self, stock_code: str, select_date: str) -> Tuple[Optional[str], Optional[float], str]:
        """
        确定买入日期和价格

        Args:
            stock_code: 股票代码
            select_date: 选股日期 (YYYYMMDD)

        Returns:
            (买入日期, 买入价格, 买入原因)
        买入原因: '正常买入', '秒板延后', '数据不足'
        """
        file_path = os.path.join(self.daily_dir, f'{stock_code}.csv')
        df = safe_read_csv(file_path)

        if df is None or df.empty:
            return None, None, '数据不足'

        # 确保日期格式正确
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # 找到选股日期后的第一个交易日
        select_date_fmt = datetime.strptime(select_date, '%Y%m%d').strftime('%Y-%m-%d')

        # 从选股日期的下一天开始查找
        future_data = df[df['date'] > select_date_fmt].sort_values('date')

        if future_data.empty:
            return None, None, '数据不足'

        # 检查是否ST股（简化判断，从stock_name中包含ST）
        is_st = 'ST' in str(stock_code)

        # 遍历未来交易日，找到第一个非秒板日
        for idx in range(len(future_data)):
            row = future_data.iloc[idx]

            # 获取前一交易日收盘价
            current_date = row['date']
            prev_data = df[df['date'] < current_date]
            if prev_data.empty:
                continue

            prev_close = prev_data.iloc[-1]['close']
            open_price = row['open']

            # 检查是否秒板
            if self.is_limit_up_open(open_price, prev_close, is_st):
                # 秒板，继续找下一天
                continue

            # 非秒板，可以买入
            return current_date, open_price, '正常买入' if idx == 0 else f'秒板延后{idx}天'

        # 所有未来交易日都是秒板，无法买入
        return None, None, '连续秒板无法买入'

    def calculate_returns(self, stock_code: str, buy_date: str, buy_price: float) -> Dict[int, Optional[float]]:
        """
        计算不同持有天数的收益率

        Returns:
            {持有天数: 收益率%, ...}
        """
        file_path = os.path.join(self.daily_dir, f'{stock_code}.csv')
        df = safe_read_csv(file_path)

        if df is None or df.empty:
            return {days: None for days in self.HOLD_DAYS}

        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('date').reset_index(drop=True)

        # 找到买入日期索引
        buy_idx = df[df['date'] == buy_date].index
        if len(buy_idx) == 0:
            return {days: None for days in self.HOLD_DAYS}

        buy_idx = buy_idx[0]
        results = {}

        for hold_days in self.HOLD_DAYS:
            sell_idx = buy_idx + hold_days

            if sell_idx >= len(df):
                results[hold_days] = None  # 数据不足
            else:
                sell_price = df.iloc[sell_idx]['close']
                return_pct = (sell_price - buy_price) / buy_price * 100
                results[hold_days] = return_pct

        return results

    def backtest_single_result(self, result_file: str) -> List[Dict]:
        """
        回测单个选股结果文件

        Returns:
            每笔交易的回测结果列表
        """
        select_date = self.parse_result_date(result_file)
        if not select_date:
            self.logger.warning(f"无法解析日期: {result_file}")
            return []

        # 读取选股结果
        df = safe_read_csv(result_file)
        if df is None or df.empty:
            self.logger.warning(f"无法读取结果文件: {result_file}")
            return []

        results = []
        code_col = '股票代码' if '股票代码' in df.columns else 'stock_code'

        for _, row in df.iterrows():
            stock_code = str(row[code_col]).zfill(6)

            # 确定买入日期和价格
            buy_date, buy_price, buy_reason = self.find_buy_date(stock_code, select_date)

            if buy_date is None:
                results.append({
                    'select_date': select_date,
                    'stock_code': stock_code,
                    'stock_name': row.get('股票名称', row.get('stock_name', '')),
                    'buy_date': None,
                    'buy_price': None,
                    'buy_reason': buy_reason,
                    'score': row.get('综合评分', row.get('total_score', 0))
                })
                continue

            # 计算收益率
            returns = self.calculate_returns(stock_code, buy_date, buy_price)

            result = {
                'select_date': select_date,
                'stock_code': stock_code,
                'stock_name': row.get('股票名称', row.get('stock_name', '')),
                'score': row.get('综合评分', row.get('total_score', 0)),
                'buy_date': buy_date,
                'buy_price': buy_price,
                'buy_reason': buy_reason
            }

            # 添加各持有期收益
            for hold_days in self.HOLD_DAYS:
                result[f'return_{hold_days}d'] = returns.get(hold_days)

            results.append(result)

        return results

    def run_backtest(self, days: int = 30) -> pd.DataFrame:
        """
        运行回测

        Args:
            days: 回测最近N天的选股结果

        Returns:
            回测结果DataFrame
        """
        # 获取历史结果文件
        result_files = glob.glob(os.path.join(self.results_dir, 'monster_stock_*.csv'))
        result_files.sort(reverse=True)  # 最新的在前

        # 选择最近N天的结果
        selected_files = result_files[:days] if len(result_files) > days else result_files

        self.logger.info(f"回测文件数: {len(selected_files)}")

        all_results = []
        for result_file in selected_files:
            self.logger.info(f"回测文件: {os.path.basename(result_file)}")
            results = self.backtest_single_result(result_file)
            all_results.extend(results)

        if not all_results:
            return pd.DataFrame()

        return pd.DataFrame(all_results)

    def generate_report(self, df: pd.DataFrame) -> str:
        """
        生成回测报告
        """
        if df.empty:
            return "无回测数据"

        lines = []
        lines.append("=" * 80)
        lines.append("选股策略回测报告")
        lines.append("=" * 80)
        lines.append(f"回测样本数: {len(df)} 笔")
        lines.append(f"可买入样本: {df['buy_date'].notna().sum()} 笔")
        lines.append("")

        # 各持有期统计
        for hold_days in self.HOLD_DAYS:
            col = f'return_{hold_days}d'
            valid_data = df[df[col].notna()]

            if valid_data.empty:
                lines.append(f"持有{hold_days}天: 无有效数据")
                continue

            returns = valid_data[col]

            win_count = (returns > 0).sum()
            total_count = len(returns)
            win_rate = win_count / total_count * 100 if total_count > 0 else 0

            avg_return = returns.mean()
            max_return = returns.max()
            min_return = returns.min()

            lines.append(f"持有{hold_days}天统计:")
            lines.append(f"  胜率: {win_rate:.1f}% ({win_count}/{total_count})")
            lines.append(f"  平均收益: {avg_return:+.2f}%")
            lines.append(f"  最大收益: {max_return:+.2f}%")
            lines.append(f"  最小收益: {min_return:+.2f}%")
            lines.append("")

        # 按评分分组统计
        lines.append("按综合评分分组（持有10天）:")
        lines.append("-" * 40)

        df['score_group'] = pd.cut(df['score'], bins=[0, 30, 40, 50, 60, 100], labels=['<30', '30-40', '40-50', '50-60', '60+'])

        for group_name, group_df in df.groupby('score_group', observed=True):
            valid_data = group_df[group_df['return_10d'].notna()]
            if valid_data.empty:
                continue

            returns = valid_data['return_10d']
            win_count = (returns > 0).sum()
            total_count = len(returns)
            win_rate = win_count / total_count * 100 if total_count > 0 else 0
            avg_return = returns.mean()

            lines.append(f"  评分{group_name}: 胜率{win_rate:.1f}%, 平均收益{avg_return:+.2f}% ({total_count}笔)")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='选股策略回测')
    parser.add_argument('--days', type=int, default=30,
                        help='回测最近N天的选股结果（默认30天）')
    parser.add_argument('--output', type=str, default='data/results/backtest_result.csv',
                        help='回测结果输出文件')
    parser.add_argument('--daily-dir', type=str, default='data/daily',
                        help='日线数据目录')
    parser.add_argument('--results-dir', type=str, default='data/results',
                        help='选股结果目录')

    args = parser.parse_args()

    print("=" * 80)
    print("选股策略回测")
    print("=" * 80)
    print(f"日线数据目录: {args.daily_dir}")
    print(f"选股结果目录: {args.results_dir}")
    print(f"回测天数: {args.days}")
    print("")

    # 创建回测器
    backtest = StrategyBacktest(
        daily_dir=args.daily_dir,
        results_dir=args.results_dir
    )

    # 运行回测
    result_df = backtest.run_backtest(days=args.days)

    if result_df.empty:
        print("回测失败: 无有效数据")
        return 1

    # 保存结果
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    result_df.to_csv(args.output, index=False, encoding='utf-8-sig')
    print(f"回测明细已保存: {args.output}")
    print("")

    # 生成报告
    report = backtest.generate_report(result_df)
    print(report)

    # 保存报告
    report_file = args.output.replace('.csv', '_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"报告已保存: {report_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
