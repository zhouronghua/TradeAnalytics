#!/usr/bin/env python3
"""
TradeAnalytics 批量分析CLI入口

用法:
    python3 batch_analyze.py                    # 完整流程: 更新数据 + 妖股筛选 + 邮件
    python3 batch_analyze.py --skip-download    # 跳过数据下载，直接分析
    python3 batch_analyze.py --no-email         # 不发送邮件
    python3 batch_analyze.py --test-email       # 仅发送测试邮件
    python3 batch_analyze.py --volume-only      # 仅成交量暴涨分析
"""

import argparse
import sys
import os
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import setup_logger, Config, is_trading_day
from src.data_downloader import DataDownloader
from src.monster_stock_analyzer import MonsterStockAnalyzer
from src.volume_analyzer import analyze_volume_surge
from src.email_sender import EmailSender


def parse_args():
    parser = argparse.ArgumentParser(description='TradeAnalytics 批量分析')
    parser.add_argument('--skip-download', action='store_true',
                        help='跳过数据下载，使用本地已有数据')
    parser.add_argument('--no-email', action='store_true',
                        help='不发送邮件')
    parser.add_argument('--test-email', action='store_true',
                        help='仅发送测试邮件')
    parser.add_argument('--volume-only', action='store_true',
                        help='仅执行成交量暴涨分析(原有逻辑)')
    parser.add_argument('--force-non-trading', action='store_true',
                        help='非交易日也执行(默认跳过周末)')
    parser.add_argument('--config', default='config/config.ini',
                        help='配置文件路径')
    return parser.parse_args()


def print_banner():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("=" * 60)
    print(f"  TradeAnalytics 批量分析")
    print(f"  {now}")
    print("=" * 60)


def download_data(config_file: str, logger) -> bool:
    """下载/更新股票数据"""
    logger.info("开始下载/更新股票数据...")
    try:
        downloader = DataDownloader(config_file)

        stock_list = downloader.download_stock_list()
        if stock_list is None or stock_list.empty:
            logger.error("下载股票列表失败")
            return False
        logger.info(f"股票列表: {len(stock_list)} 只")

        def progress(current, total, stock_code, matched):
            if current % 500 == 0:
                logger.info(f"  下载进度: {current}/{total}")

        success, fail = downloader.download_all_stocks(
            stock_list, callback=progress)
        logger.info(f"数据下载完成: 成功{success}, 失败{fail}")
        return True

    except Exception as e:
        logger.error(f"数据下载失败: {e}")
        return False


def run_monster_analysis(config_file: str, logger):
    """运行妖股筛选"""
    config = Config(config_file)
    analyzer = MonsterStockAnalyzer(config)
    daily_dir = config.get('Paths', 'daily_dir', fallback='./data/daily')
    results_dir = config.get('Paths', 'results_dir', fallback='./data/results')

    def progress(current, total, message):
        if current % 500 == 0 or current == total:
            logger.info(f"  {message}")

    results_df, output_file = analyzer.run(daily_dir, results_dir, progress)
    return results_df, output_file


def run_volume_analysis(config_file: str, logger):
    """运行成交量暴涨分析"""
    config = Config(config_file)
    daily_dir = config.get('Paths', 'daily_dir', fallback='./data/daily')
    results_dir = config.get('Paths', 'results_dir', fallback='./data/results')

    csv_files = glob.glob(os.path.join(daily_dir, '*.csv'))
    if not csv_files:
        logger.warning("未找到股票数据文件")
        return None, None

    logger.info(f"开始成交量暴涨分析: {len(csv_files)} 只股票")

    def progress(current, total, message):
        if current % 500 == 0 or current == total:
            logger.info(f"  {message}")

    results_df = analyze_volume_surge(csv_files, progress)

    if results_df.empty:
        logger.info("未发现符合条件的股票")
        return results_df, None

    os.makedirs(results_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(results_dir, f'volume_surge_{ts}.csv')
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"成交量分析完成: {len(results_df)} 只, 保存 {output_file}")
    return results_df, output_file


def main():
    args = parse_args()
    print_banner()

    logger = setup_logger('BatchAnalyze')

    # 测试邮件模式
    if args.test_email:
        logger.info("发送测试邮件...")
        sender = EmailSender(args.config)
        if sender.send_test():
            print("[OK] 测试邮件发送成功")
        else:
            print("[FAIL] 测试邮件发送失败，请检查config.ini中[Email]配置")
        return

    # 交易日检查
    if not args.force_non_trading and not is_trading_day(datetime.now()):
        logger.info("今天不是交易日，跳过分析 (使用 --force-non-trading 可强制执行)")
        return

    # 步骤1: 下载数据
    if not args.skip_download:
        daily_dir = Config(args.config).get('Paths', 'daily_dir', fallback='./data/daily')
        csv_count = len(glob.glob(os.path.join(daily_dir, '*.csv')))
        if csv_count == 0:
            logger.info("本地无数据，必须先下载")
            if not download_data(args.config, logger):
                logger.error("数据下载失败，退出")
                sys.exit(1)
        else:
            logger.info(f"本地已有 {csv_count} 只股票数据，尝试增量更新...")
            download_data(args.config, logger)
    else:
        logger.info("跳过数据下载")

    # 步骤2: 分析
    if args.volume_only:
        logger.info("--- 成交量暴涨分析 ---")
        results_df, output_file = run_volume_analysis(args.config, logger)
    else:
        logger.info("--- 妖股综合筛选 ---")
        results_df, output_file = run_monster_analysis(args.config, logger)

    # 步骤3: 输出结果摘要
    if results_df is not None and not results_df.empty:
        print(f"\n发现 {len(results_df)} 只候选股:")
        print("-" * 80)
        display_cols = ['stock_code', 'stock_name', 'close', 'change_pct',
                        'volume_ratio', 'total_score', 'consecutive_limits']
        display_cols = [c for c in display_cols if c in results_df.columns]
        print(results_df[display_cols].head(20).to_string(index=False))
        print("-" * 80)
        if output_file:
            print(f"完整结果: {output_file}")
    else:
        print("\n未发现符合条件的候选股")

    # 步骤4: 发送邮件
    if not args.no_email:
        logger.info("--- 发送邮件 ---")
        sender = EmailSender(args.config)
        if sender.enabled:
            today = datetime.now().strftime('%Y-%m-%d')
            if sender.send_monster_stock_report(results_df, today):
                print("[OK] 分析报告邮件已发送")
            else:
                print("[FAIL] 邮件发送失败")
        else:
            logger.info("邮件功能未启用(config.ini [Email] enabled=false)")

    print("\n分析完成.")


if __name__ == '__main__':
    main()
