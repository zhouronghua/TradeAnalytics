"""
下载2020年以来所有A股历史日线数据
用于回测妖股策略
"""

import os
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_downloader import DataDownloader
from src.utils import setup_logger


def download_all_history(start_year: int = 2020):
    """下载所有股票的历史数据"""
    logger = setup_logger('DownloadHistory')

    # 创建下载器
    downloader = DataDownloader()

    # 先更新股票列表
    logger.info("更新股票列表...")
    stock_list = downloader.download_stock_list(force_update=True)

    if stock_list is None or stock_list.empty:
        logger.error("获取股票列表失败")
        return

    total_stocks = len(stock_list)
    logger.info(f"股票列表获取成功，共 {total_stocks} 只股票")

    # 计算下载日期范围
    start_date = f"{start_year}0101"
    end_date = datetime.now().strftime('%Y%m%d')

    logger.info(f"下载时间范围: {start_date} ~ {end_date}")
    logger.info(f"预计下载 {total_stocks} 只股票的历史数据...")

    # 统计
    success_count = 0
    fail_count = 0
    skip_count = 0

    # 使用单线程下载避免被封（根据配置）
    max_workers = downloader.max_workers
    logger.info(f"使用 {max_workers} 个线程下载")

    def download_single(stock_code: str) -> bool:
        """下载单只股票"""
        nonlocal success_count, fail_count, skip_count
        try:
            file_path = os.path.join(downloader.daily_dir, f"{stock_code}.csv")

            # 检查是否已有数据
            if os.path.exists(file_path):
                # 读取现有数据查看最新日期
                import pandas as pd
                df = pd.read_csv(file_path)
                if not df.empty:
                    latest_date = pd.to_datetime(df['date']).max()
                    latest_str = latest_date.strftime('%Y%m%d')

                    # 如果数据已经包含2020年以来的最新数据，跳过
                    if latest_str >= end_date or latest_str >= str(int(end_date) - 1):
                        skip_count += 1
                        if (success_count + fail_count + skip_count) % 100 == 0:
                            logger.info(f"进度: {success_count + fail_count + skip_count}/{total_stocks}, "
                                      f"成功:{success_count}, 失败:{fail_count}, 跳过:{skip_count}")
                        return True

            # 下载历史数据
            df = downloader.download_stock_history(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and not df.empty:
                # 保存数据
                if downloader.save_stock_data(stock_code, df):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1

            # 每100只报告一次进度
            if (success_count + fail_count + skip_count) % 100 == 0:
                logger.info(f"进度: {success_count + fail_count + skip_count}/{total_stocks}, "
                          f"成功:{success_count}, 失败:{fail_count}, 跳过:{skip_count}")

            return True

        except Exception as e:
            logger.error(f"下载 {stock_code} 失败: {e}")
            fail_count += 1
            return False

    # 使用线程池下载
    stock_codes = stock_list['code'].tolist()

    if max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(download_single, code): code for code in stock_codes}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"下载异常: {e}")
    else:
        # 单线程模式
        for code in stock_codes:
            download_single(code)
            time.sleep(0.5)  # 避免请求过快

    logger.info("=" * 60)
    logger.info("下载完成!")
    logger.info(f"总计: {total_stocks} 只")
    logger.info(f"成功: {success_count} 只")
    logger.info(f"失败: {fail_count} 只")
    logger.info(f"跳过: {skip_count} 只 (已有数据)")
    logger.info("=" * 60)


if __name__ == '__main__':
    print("=" * 60)
    print("下载2020年以来A股历史日线数据")
    print("=" * 60)
    print()

    # 确认下载
    #confirm = input("确认下载2020年以来所有A股日线数据? (y/n): ")
    #if confirm.lower() == 'y':
    download_all_history(start_year=2020)
    #else:
    #    print("已取消下载")
