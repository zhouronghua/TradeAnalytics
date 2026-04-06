#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增量下载A股历史日线数据
支持从2020年开始下载，后续只做增量更新
默认数据源: AkShare (无需Token，开源免费)
也可选用: Tushare Pro / BaoStock
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加src到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_downloader import DataDownloader
from src.utils import setup_logger, safe_read_csv, safe_write_csv, ensure_dir


def get_data_date_range(file_path: str) -> tuple:
    """
    获取本地数据文件的日期范围

    Returns:
        (最早日期, 最新日期) 或 (None, None)
    """
    try:
        df = safe_read_csv(file_path)
        if df is None or df.empty:
            return None, None

        dates = pd.to_datetime(df['date'])
        return dates.min().strftime('%Y-%m-%d'), dates.max().strftime('%Y-%m-%d')
    except:
        return None, None


def download_stock_incremental(downloader: DataDownloader, stock_code: str,
                               start_date: str, end_date: str,
                               rate_limiter=None) -> bool:
    """
    增量下载单只股票数据

    Args:
        downloader: 数据下载器
        stock_code: 股票代码
        start_date: 数据起始日期 'YYYY-MM-DD'（首次下载用2020-01-01）
        end_date: 数据结束日期 'YYYY-MM-DD'
        rate_limiter: 限流控制器（用于多线程下载时控制频率）

    Returns:
        是否成功
    """
    # AkShare限流 - 每只股票下载前等待
    if downloader.data_source == 'akshare' and rate_limiter is not None:
        import time
        with rate_limiter:
            time.sleep(0.5)  # 每只间隔0.5秒

    logger = setup_logger('IncrementalDownload')
    file_path = os.path.join(downloader.daily_dir, f"{stock_code}.csv")

    # 检查本地数据
    if os.path.exists(file_path):
        earliest, latest = get_data_date_range(file_path)

        if earliest and latest:
            # 已有数据，检查是否需要补充历史或更新最新
            if earliest > start_date:
                # 需要补充历史数据
                logger.debug(f"{stock_code}: 补充历史数据 {start_date} 到 {earliest}")
                hist_df = downloader.download_stock_history(
                    stock_code, start_date=start_date.replace('-', ''),
                    end_date=(pd.to_datetime(earliest) - timedelta(days=1)).strftime('%Y%m%d')
                )

                if hist_df is not None and not hist_df.empty:
                    # 合并数据
                    local_df = safe_read_csv(file_path)
                    combined = pd.concat([hist_df, local_df], ignore_index=True)
                    combined.drop_duplicates(subset=['date'], keep='last', inplace=True)
                    combined.sort_values('date', inplace=True)
                    safe_write_csv(combined, file_path)
                    logger.debug(f"{stock_code}: 补充 {len(hist_df)} 条历史数据")

            # 更新最新数据
            if latest < end_date:
                next_date = (pd.to_datetime(latest) + timedelta(days=1)).strftime('%Y%m%d')
                logger.debug(f"{stock_code}: 更新数据 {next_date} 到 {end_date}")
                new_df = downloader.download_stock_history(
                    stock_code, start_date=next_date, end_date=end_date.replace('-', '')
                )

                if new_df is not None and not new_df.empty:
                    local_df = safe_read_csv(file_path)
                    combined = pd.concat([local_df, new_df], ignore_index=True)
                    combined.drop_duplicates(subset=['date'], keep='last', inplace=True)
                    combined.sort_values('date', inplace=True)
                    safe_write_csv(combined, file_path)
                    return True
                else:
                    # 无新数据，但本地数据有效
                    return True
            else:
                # 数据已最新
                return True
        else:
            # 文件存在但无法解析，重新下载全部
            logger.warning(f"{stock_code}: 本地数据损坏，重新下载")
    else:
        # 无本地数据，首次全量下载
        logger.debug(f"{stock_code}: 首次下载 {start_date} 到 {end_date}")

    # 全量下载
    df = downloader.download_stock_history(
        stock_code, start_date=start_date.replace('-', ''),
        end_date=end_date.replace('-', '')
    )

    if df is not None and not df.empty:
        safe_write_csv(df, file_path)
        return True

    return False


def download_all_incremental(start_year: int = 2020, max_workers: int = 5,
                            data_source: str = 'tushare',
                            tushare_token: str = None) -> dict:
    """
    增量下载所有A股历史数据

    Args:
        start_year: 起始年份，默认2020
        max_workers: 并发下载数
        data_source: 数据源 'tushare'/'akshare'/'baostock'
        tushare_token: Tushare Pro Token

    Returns:
        统计信息字典
    """
    logger = setup_logger('IncrementalDownload')

    # 日期设置
    start_date = f"{start_year}-01-01"
    end_date = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"开始增量下载A股数据")
    logger.info(f"数据源: {data_source}")
    logger.info(f"数据范围: {start_date} 至 {end_date}")
    logger.info(f"并发数: {max_workers}")

    # 初始化下载器
    downloader = DataDownloader()
    downloader.data_source = data_source

    # 配置Tushare
    if data_source == 'tushare':
        from src.data_source_tushare import TushareDataSource
        try:
            token = tushare_token or os.environ.get('TUSHARE_TOKEN')
            downloader.tushare_source = TushareDataSource(token=token)
            logger.info("使用Tushare Pro数据源")
        except Exception as e:
            logger.error(f"Tushare初始化失败: {e}")
            logger.info("切换到AkShare")
            downloader.data_source = 'akshare'

    # 获取股票列表
    stock_list = downloader.download_stock_list()
    if stock_list is None or stock_list.empty:
        logger.error("无法获取股票列表")
        return {'success': 0, 'failed': 0, 'skipped': 0}

    total = len(stock_list)
    logger.info(f"共 {total} 只股票需要处理")

    # 统计
    stats = {
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'new_download': 0,
        'updated': 0,
        'already_latest': 0
    }

    # AkShare限流提示
    if data_source == 'akshare':
        logger.info("AkShare数据源: 东方财富接口有频率限制")
        logger.info("建议: 使用 --workers 1 单线程下载，首次下载约需2-3小时")
        if max_workers > 2:
            logger.warning(f"当前并发数 {max_workers} 过高，建议降低为 1-2 避免被限流")

    # 进度显示 - 更频繁地显示
    def show_progress(force=False):
        processed = stats['success'] + stats['failed']
        if force or processed % 50 == 0 or processed == total:
            pct = processed / total * 100
            logger.info(f"进度: {processed}/{total} ({pct:.1f}%) "
                       f"成功:{stats['success']} 失败:{stats['failed']} "
                       f"新下载:{stats['new_download']} 更新:{stats['updated']} 已最新:{stats['already_latest']}")

    # 下载计数器（用于AkShare限流）
    download_count = [0]

    def download_one(row):
        stock_code = str(row['code'])
        try:
            file_path = os.path.join(downloader.daily_dir, f"{stock_code}.csv")

            if os.path.exists(file_path):
                earliest, latest = get_data_date_range(file_path)
                if earliest and latest:
                    # 检查数据完整性和最新性
                    expected_latest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                    if latest >= expected_latest:
                        # 数据已最新
                        stats['already_latest'] += 1
                        show_progress()
                        return True

            # AkShare限流 - 每10只休息1秒
            if data_source == 'akshare' and max_workers <= 1:
                import time
                download_count[0] += 1
                if download_count[0] % 10 == 0:
                    time.sleep(1)
                    logger.debug(f"AkShare限流: 已下载 {download_count[0]} 只，休息1秒")

            # 执行下载
            if download_stock_incremental(downloader, stock_code, start_date, end_date):
                stats['success'] += 1

                # 判断是更新还是新下载
                if os.path.exists(file_path):
                    _, latest = get_data_date_range(file_path)
                    expected_latest = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                    if latest >= expected_latest:
                        stats['updated'] += 1
                    else:
                        stats['new_download'] += 1
                else:
                    stats['new_download'] += 1

                show_progress()
                return True
            else:
                stats['failed'] += 1
                show_progress()
                return False

        except Exception as e:
            logger.error(f"下载 {stock_code} 异常: {e}")
            stats['failed'] += 1
            show_progress()
            return False

    # 下载模式选择
    if data_source == 'akshare' or max_workers == 1:
        # 单线程顺序下载（适合AkShare限流）
        logger.info("使用单线程顺序下载模式...")
        for idx, row in stock_list.iterrows():
            download_one(row)
            if (idx + 1) % 500 == 0:
                logger.info(f"已处理 {idx+1}/{total} 只股票，短暂休息...")
                import time
                time.sleep(2)  # 每500只休息2秒
    else:
        # 多线程并发下载（Tushare/BaoStock）
        logger.info(f"使用多线程并发下载（并发数: {max_workers}）...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(download_one, row): row['code']
                      for _, row in stock_list.iterrows()}

            for future in as_completed(futures):
                try:
                    future.result(timeout=60)
                except Exception as e:
                    logger.error(f"任务异常: {e}")

    # 最终统计
    logger.info("=" * 60)
    logger.info("下载完成统计:")
    logger.info(f"  总股票数: {total}")
    logger.info(f"  成功: {stats['success']}")
    logger.info(f"  失败: {stats['failed']}")
    logger.info(f"  新下载: {stats['new_download']}")
    logger.info(f"  更新: {stats['updated']}")
    logger.info(f"  已最新: {stats['already_latest']}")
    logger.info("=" * 60)

    return stats


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='增量下载A股历史数据')
    parser.add_argument('--source', type=str, default='akshare',
                       choices=['akshare', 'baostock', 'tushare'],
                       help='数据源 (默认: akshare)')
    parser.add_argument('--start-year', type=int, default=2020,
                       help='起始年份 (默认: 2020)')
    parser.add_argument('--workers', type=int, default=1,
                       help='并发下载数，AkShare建议1 (默认: 1)')
    parser.add_argument('--token', type=str, default=None,
                       help='Tushare Pro Token (也可设置环境变量TUSHARE_TOKEN)')

    args = parser.parse_args()

    # 设置环境变量token
    if args.token:
        os.environ['TUSHARE_TOKEN'] = args.token

    # 开始下载
    stats = download_all_incremental(
        start_year=args.start_year,
        max_workers=args.workers,
        data_source=args.source,
        tushare_token=args.token
    )

    return 0 if stats['failed'] < stats['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
