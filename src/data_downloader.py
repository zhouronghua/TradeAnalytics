"""
数据下载模块
支持多种数据源：AkShare、BaoStock
"""

import pandas as pd
import time
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Tuple
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, Config, safe_read_csv, safe_write_csv, ensure_dir

# 根据配置动态导入数据源
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

try:
    from src.data_source_baostock_threadsafe import ThreadSafeBaoStockDataSource as BaoStockDataSource
    BAOSTOCK_AVAILABLE = True
except ImportError:
    BAOSTOCK_AVAILABLE = False


class DataDownloader:
    """数据下载器"""
    
    def __init__(self, config_file: str = 'config/config.ini'):
        """
        初始化数据下载器
        
        Args:
            config_file: 配置文件路径
        """
        self.config = Config(config_file)
        self.logger = setup_logger('DataDownloader')
        
        # 读取配置
        self.data_dir = self.config.get('Paths', 'data_dir', fallback='./data')
        self.daily_dir = self.config.get('Paths', 'daily_dir', fallback='./data/daily')
        self.stocks_dir = self.config.get('Paths', 'stocks_dir', fallback='./data/stocks')
        self.max_workers = self.config.getint('Download', 'max_workers', fallback=10)
        self.retry_times = self.config.getint('Download', 'retry_times', fallback=3)
        self.retry_delay = self.config.getint('Download', 'retry_delay', fallback=5)
        self.min_history_days = self.config.getint('Analysis', 'min_history_days', fallback=150)
        self.daily_download_limit_mb = self.config.getint('Download', 'daily_download_limit_mb', fallback=100)
        
        # 下载统计
        self.downloaded_bytes = 0
        self.download_limit_bytes = self.daily_download_limit_mb * 1024 * 1024
        
        # 确保目录存在
        ensure_dir(self.daily_dir)
        ensure_dir(self.stocks_dir)
        
        # 初始化数据源
        self.data_source = self.config.get('DataSource', 'source', fallback='akshare').lower()
        self.baostock_source = None
        
        if self.data_source == 'baostock':
            if not BAOSTOCK_AVAILABLE:
                self.logger.error("BaoStock不可用，请安装: pip install baostock")
                self.logger.info("自动切换到AkShare")
                self.data_source = 'akshare'
            else:
                self.baostock_source = BaoStockDataSource()
                self.logger.info("使用BaoStock数据源（线程安全版本）")
        elif self.data_source == 'akshare':
            if not AKSHARE_AVAILABLE:
                self.logger.error("AkShare不可用，请安装: pip install akshare")
                if BAOSTOCK_AVAILABLE:
                    self.logger.info("自动切换到BaoStock")
                    self.data_source = 'baostock'
                    self.baostock_source = BaoStockDataSource()
            else:
                self.logger.info("使用AkShare数据源")
        
        self.logger.info(f"数据下载器初始化完成（每日下载限制: {self.daily_download_limit_mb}MB）")
    
    def download_stock_list(self, force_update: bool = False) -> Optional[pd.DataFrame]:
        """
        下载股票列表
        
        Args:
            force_update: 是否强制更新
        
        Returns:
            股票列表DataFrame
        """
        stock_list_file = os.path.join(self.stocks_dir, 'stock_list.csv')
        
        # 检查是否需要更新
        if not force_update and os.path.exists(stock_list_file):
            file_time = datetime.fromtimestamp(os.path.getmtime(stock_list_file))
            update_days = self.config.getint('DataSource', 'update_stock_list_days', fallback=1)
            if (datetime.now() - file_time).days < update_days:
                self.logger.info("股票列表缓存有效，从本地读取")
                # 读取时指定code列为字符串类型
                return safe_read_csv(stock_list_file, dtype={'code': str})
        
        # 下载股票列表
        self.logger.info(f"开始下载股票列表（数据源: {self.data_source}）...")
        
        stock_list = None
        
        try:
            if self.data_source == 'baostock' and self.baostock_source:
                # 使用BaoStock（线程安全版本会自动处理登录）
                stock_list = self.baostock_source.get_stock_list()
                
            elif self.data_source == 'akshare':
                # 使用AkShare
                stock_list = ak.stock_zh_a_spot_em()
                
                if stock_list is not None and not stock_list.empty:
                    # 选择需要的列并重命名
                    columns_map = {
                        '代码': 'code',
                        '名称': 'name',
                        '最新价': 'price',
                        '涨跌幅': 'change_pct',
                        '成交量': 'volume',
                        '成交额': 'amount',
                        '总市值': 'total_value'
                    }
                    
                    # 只保留存在的列
                    available_columns = {k: v for k, v in columns_map.items() if k in stock_list.columns}
                    stock_list = stock_list[list(available_columns.keys())].copy()
                    stock_list.rename(columns=available_columns, inplace=True)
            
            if stock_list is None or stock_list.empty:
                self.logger.error("获取股票列表失败")
                # 尝试读取本地缓存
                if os.path.exists(stock_list_file):
                    self.logger.info("从本地缓存读取股票列表")
                    return safe_read_csv(stock_list_file, dtype={'code': str})
                return None
            
            # 确保code列为字符串类型
            stock_list['code'] = stock_list['code'].astype(str)
            
            # 添加市场标识（根据代码前缀）
            stock_list['market'] = stock_list['code'].apply(self._get_market)
            
            # 保存到本地
            if safe_write_csv(stock_list, stock_list_file):
                self.logger.info(f"股票列表下载成功，共 {len(stock_list)} 只股票")
            else:
                self.logger.error("股票列表保存失败")
                return None
            
            return stock_list
            
        except Exception as e:
            self.logger.error(f"下载股票列表异常: {e}")
            # 尝试读取本地缓存
            if os.path.exists(stock_list_file):
                self.logger.info("从本地缓存读取股票列表")
                # 读取时指定code列为字符串类型
                return safe_read_csv(stock_list_file, dtype={'code': str})
            return None
    
    def _get_market(self, code: str) -> str:
        """
        根据股票代码判断市场
        
        Args:
            code: 股票代码
        
        Returns:
            市场标识 (SH/SZ/BJ)
        """
        if code.startswith('6'):
            return 'SH'  # 上海
        elif code.startswith(('0', '3')):
            return 'SZ'  # 深圳
        elif code.startswith(('4', '8')):
            return 'BJ'  # 北京
        else:
            return 'UNKNOWN'
    
    def download_stock_history(self, stock_code: str, period: str = "daily",
                               start_date: str = None, end_date: str = None,
                               adjust: str = "qfq") -> Optional[pd.DataFrame]:
        """
        下载单只股票的历史数据
        
        Args:
            stock_code: 股票代码
            period: 周期 (daily/weekly/monthly)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            adjust: 复权类型 (qfq=前复权, hfq=后复权, None=不复权)
        
        Returns:
            历史数据DataFrame
        """
        # 设置默认日期范围
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=self.min_history_days)).strftime('%Y%m%d')
        
        # 格式化日期
        start_date_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        end_date_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
        
        # 重试机制
        for attempt in range(self.retry_times):
            try:
                df = None
                
                if self.data_source == 'baostock' and self.baostock_source:
                    # 使用BaoStock（线程安全版本会自动处理登录）
                    df = self.baostock_source.get_stock_history(
                        stock_code=stock_code,
                        start_date=start_date_fmt,
                        end_date=end_date_fmt
                    )
                    
                elif self.data_source == 'akshare':
                    # 使用AkShare下载数据
                    df = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period=period,
                        start_date=start_date_fmt,
                        end_date=end_date_fmt,
                        adjust=adjust
                    )
                    
                    if df is not None and not df.empty:
                        # 标准化列名
                        columns_map = {
                            '日期': 'date',
                            '开盘': 'open',
                            '收盘': 'close',
                            '最高': 'high',
                            '最低': 'low',
                            '成交量': 'volume',
                            '成交额': 'amount',
                            '振幅': 'amplitude',
                            '涨跌幅': 'change_pct',
                            '涨跌额': 'change',
                            '换手率': 'turnover'
                        }
                        
                        # 只保留存在的列
                        available_columns = {k: v for k, v in columns_map.items() if k in df.columns}
                        df = df[list(available_columns.keys())].copy()
                        df.rename(columns=available_columns, inplace=True)
                        
                        # 转换日期格式
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                
                if df is None or df.empty:
                    self.logger.warning(f"股票 {stock_code} 数据为空")
                    return None
                
                # 统计下载数据量（在成功下载后）
                if df is not None and not df.empty:
                    # 估算CSV文件大小（每行约100字节）
                    estimated_size = len(df) * 100
                    self.downloaded_bytes += estimated_size
                
                return df
                
            except Exception as e:
                self.logger.warning(f"下载股票 {stock_code} 数据失败 (尝试 {attempt + 1}/{self.retry_times}): {e}")
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"股票 {stock_code} 下载失败，已达最大重试次数")
                    return None
    
    def save_stock_data(self, stock_code: str, df: pd.DataFrame) -> bool:
        """
        保存股票数据到本地
        
        Args:
            stock_code: 股票代码
            df: 数据DataFrame
        
        Returns:
            是否成功
        """
        file_path = os.path.join(self.daily_dir, f"{stock_code}.csv")
        return safe_write_csv(df, file_path)
    
    def check_download_limit(self) -> bool:
        """
        检查是否超过下载限制
        
        Returns:
            是否可以继续下载
        """
        # 如果限制为0，表示无限制
        if self.daily_download_limit_mb == 0:
            return True
            
        if self.downloaded_bytes >= self.download_limit_bytes:
            downloaded_mb = self.downloaded_bytes / 1024 / 1024
            self.logger.warning(f"已达到每日下载限制 ({downloaded_mb:.2f}MB / {self.daily_download_limit_mb}MB)")
            return False
        return True
    
    def get_download_stats(self) -> dict:
        """
        获取下载统计信息
        
        Returns:
            统计信息字典
        """
        downloaded_mb = self.downloaded_bytes / 1024 / 1024
        limit_mb = self.download_limit_bytes / 1024 / 1024
        percentage = (self.downloaded_bytes / self.download_limit_bytes * 100) if self.download_limit_bytes > 0 else 0
        
        return {
            'downloaded_bytes': self.downloaded_bytes,
            'downloaded_mb': downloaded_mb,
            'limit_mb': limit_mb,
            'percentage': percentage,
            'remaining_mb': limit_mb - downloaded_mb
        }
    
    def update_stock_data(self, stock_code: str) -> bool:
        """
        增量更新单只股票数据
        
        Args:
            stock_code: 股票代码
        
        Returns:
            是否成功
        """
        # 检查下载限制
        if not self.check_download_limit():
            self.logger.info(f"下载限制已达到，跳过股票 {stock_code}")
            return False
        
        file_path = os.path.join(self.daily_dir, f"{stock_code}.csv")
        
        # 检查本地数据
        local_df = safe_read_csv(file_path)
        
        if local_df is not None and not local_df.empty:
            # 获取最新日期
            latest_date = pd.to_datetime(local_df['date']).max()
            start_date = (latest_date + timedelta(days=1)).strftime('%Y%m%d')
            
            # 检查是否需要更新
            if start_date >= datetime.now().strftime('%Y%m%d'):
                self.logger.debug(f"股票 {stock_code} 数据已是最新")
                return True
            
            # 下载增量数据
            new_df = self.download_stock_history(stock_code, start_date=start_date)
            
            if new_df is not None and not new_df.empty:
                # 合并数据
                combined_df = pd.concat([local_df, new_df], ignore_index=True)
                combined_df.drop_duplicates(subset=['date'], keep='last', inplace=True)
                combined_df.sort_values('date', inplace=True)
                
                return self.save_stock_data(stock_code, combined_df)
            else:
                # 没有新数据或下载失败
                return True
        else:
            # 本地无数据，下载全部历史数据
            df = self.download_stock_history(stock_code)
            if df is not None:
                return self.save_stock_data(stock_code, df)
            return False
    
    def download_all_stocks(self, stock_list: pd.DataFrame = None,
                           callback=None) -> Tuple[int, int]:
        """
        批量下载所有股票数据
        
        Args:
            stock_list: 股票列表，如果为None则自动获取
            callback: 进度回调函数 (current, total, stock_code, success)
        
        Returns:
            (成功数量, 失败数量)
        """
        if stock_list is None:
            stock_list = self.download_stock_list()
            if stock_list is None:
                self.logger.error("无法获取股票列表")
                return 0, 0
        
        # 确保code列为字符串类型
        if 'code' in stock_list.columns:
            stock_list['code'] = stock_list['code'].astype(str)
        
        total = len(stock_list)
        success_count = 0
        fail_count = 0
        
        self.logger.info(f"开始下载 {total} 只股票数据...")
        
        def download_single(index: int, row: pd.Series) -> Tuple[str, bool]:
            """下载单只股票"""
            stock_code = str(row['code'])  # 确保是字符串
            try:
                result = self.update_stock_data(stock_code)
                if callback:
                    callback(index + 1, total, stock_code, result)
                return stock_code, result
            except Exception as e:
                self.logger.error(f"下载股票 {stock_code} 异常: {e}")
                if callback:
                    callback(index + 1, total, stock_code, False)
                return stock_code, False
        
        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(download_single, idx, row): row['code']
                for idx, row in stock_list.iterrows()
            }
            
            for future in as_completed(futures):
                stock_code, success = future.result()
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                
                # 每下载100只股票输出一次进度
                if (success_count + fail_count) % 100 == 0:
                    self.logger.info(f"进度: {success_count + fail_count}/{total}, "
                                   f"成功: {success_count}, 失败: {fail_count}")
        
        # 输出下载统计
        stats = self.get_download_stats()
        self.logger.info(f"下载完成！成功: {success_count}, 失败: {fail_count}")
        self.logger.info(f"下载数据量: {stats['downloaded_mb']:.2f}MB / {stats['limit_mb']:.0f}MB ({stats['percentage']:.1f}%)")
        
        return success_count, fail_count
    
    def get_latest_data_date(self) -> Optional[str]:
        """
        获取本地数据的最新日期
        
        Returns:
            最新日期字符串 (YYYY-MM-DD)
        """
        try:
            latest_date = None
            for filename in os.listdir(self.daily_dir):
                if not filename.endswith('.csv'):
                    continue
                
                file_path = os.path.join(self.daily_dir, filename)
                df = safe_read_csv(file_path)
                
                if df is not None and not df.empty and 'date' in df.columns:
                    file_latest = pd.to_datetime(df['date']).max()
                    if latest_date is None or file_latest > latest_date:
                        latest_date = file_latest
            
            return latest_date.strftime('%Y-%m-%d') if latest_date else None
        except Exception as e:
            self.logger.error(f"获取最新数据日期失败: {e}")
            return None


def main():
    """测试代码"""
    downloader = DataDownloader()
    
    # 下载股票列表
    print("下载股票列表...")
    stock_list = downloader.download_stock_list(force_update=True)
    if stock_list is not None:
        print(f"股票列表: {len(stock_list)} 只")
        print(stock_list.head())
    
    # 下载单只股票测试
    print("\n下载单只股票测试 (平安银行 000001)...")
    df = downloader.download_stock_history('000001')
    if df is not None:
        print(f"数据行数: {len(df)}")
        print(df.head())
        print(df.tail())
        downloader.save_stock_data('000001', df)
    
    # 获取最新数据日期
    latest_date = downloader.get_latest_data_date()
    print(f"\n本地最新数据日期: {latest_date}")


if __name__ == '__main__':
    main()
