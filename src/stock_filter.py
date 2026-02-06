"""
股票筛选模块
筛选符合条件的股票并保存结果
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, Config, safe_read_csv, safe_write_csv, ensure_dir
from src.data_analyzer import DataAnalyzer


class StockFilter:
    """股票筛选器"""
    
    def __init__(self, config_file: str = 'config/config.ini'):
        """
        初始化股票筛选器
        
        Args:
            config_file: 配置文件路径
        """
        self.config = Config(config_file)
        self.logger = setup_logger('StockFilter')
        
        # 读取配置
        self.daily_dir = self.config.get('Paths', 'daily_dir', fallback='./data/daily')
        self.stocks_dir = self.config.get('Paths', 'stocks_dir', fallback='./data/stocks')
        self.results_dir = self.config.get('Paths', 'results_dir', fallback='./data/results')
        self.ma_period = self.config.getint('Analysis', 'ma_period', fallback=120)
        self.volume_ratio_threshold = self.config.getfloat('Analysis', 'volume_ratio_threshold', fallback=5.0)
        self.max_workers = self.config.getint('Download', 'max_workers', fallback=10)
        
        # 初始化分析器
        self.analyzer = DataAnalyzer(ma_period=self.ma_period)
        
        # 确保目录存在
        ensure_dir(self.results_dir)
        
        self.logger.info(f"股票筛选器初始化完成 (MA={self.ma_period}, 成交量倍数>={self.volume_ratio_threshold})")
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表
        
        Returns:
            股票列表DataFrame
        """
        stock_list_file = os.path.join(self.stocks_dir, 'stock_list.csv')
        
        if not os.path.exists(stock_list_file):
            self.logger.error(f"股票列表文件不存在: {stock_list_file}")
            return None
        
        # 读取时指定code列为字符串类型
        return safe_read_csv(stock_list_file, dtype={'code': str})
    
    def filter_single_stock(self, stock_code: str, stock_name: str = None) -> Optional[Dict]:
        """
        筛选单只股票
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称（可选）
        
        Returns:
            如果符合条件返回详细信息字典，否则返回None
        """
        try:
            file_path = os.path.join(self.daily_dir, f"{stock_code}.csv")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.logger.debug(f"股票 {stock_code} 数据文件不存在")
                return None
            
            # 使用分析器检查条件
            is_match, info = self.analyzer.analyze_from_file(
                file_path,
                volume_ratio_threshold=self.volume_ratio_threshold,
                ma_period=self.ma_period
            )
            
            if is_match and info:
                # 添加股票代码和名称
                info['code'] = stock_code
                info['name'] = stock_name if stock_name else stock_code
                return info
            
            return None
            
        except Exception as e:
            self.logger.error(f"筛选股票 {stock_code} 失败: {e}")
            return None
    
    def filter_all_stocks(self, stock_list: pd.DataFrame = None,
                         callback: Callable = None) -> List[Dict]:
        """
        筛选所有股票
        
        Args:
            stock_list: 股票列表，如果为None则自动获取
            callback: 进度回调函数 (current, total, stock_code, matched)
        
        Returns:
            符合条件的股票列表
        """
        if stock_list is None:
            stock_list = self.get_stock_list()
            if stock_list is None:
                self.logger.error("无法获取股票列表")
                return []
        
        # 确保code列为字符串类型
        if 'code' in stock_list.columns:
            stock_list['code'] = stock_list['code'].astype(str)
        
        total = len(stock_list)
        matched_stocks = []
        processed = 0
        
        self.logger.info(f"开始筛选 {total} 只股票...")
        
        def filter_single(row: pd.Series) -> Optional[Dict]:
            """筛选单只股票的包装函数"""
            nonlocal processed
            stock_code = str(row['code'])  # 确保是字符串
            stock_name = row.get('name', stock_code)
            
            result = self.filter_single_stock(stock_code, stock_name)
            
            processed += 1
            if callback:
                callback(processed, total, stock_code, result is not None)
            
            return result
        
        # 使用线程池并发筛选
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(filter_single, row): row['code']
                for _, row in stock_list.iterrows()
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        matched_stocks.append(result)
                except Exception as e:
                    stock_code = futures[future]
                    self.logger.error(f"处理股票 {stock_code} 异常: {e}")
            
            # 每筛选100只股票输出一次进度
            if processed % 100 == 0:
                self.logger.info(f"进度: {processed}/{total}, 匹配: {len(matched_stocks)}")
        
        self.logger.info(f"筛选完成！匹配 {len(matched_stocks)} 只股票")
        return matched_stocks
    
    def save_results(self, matched_stocks: List[Dict], 
                    output_file: str = None) -> bool:
        """
        保存筛选结果
        
        Args:
            matched_stocks: 符合条件的股票列表
            output_file: 输出文件路径，如果为None则使用默认路径
        
        Returns:
            是否成功
        """
        if not matched_stocks:
            self.logger.warning("没有符合条件的股票需要保存")
            return False
        
        try:
            # 默认输出文件名：filtered_YYYYMMDD.csv
            if output_file is None:
                date_str = datetime.now().strftime('%Y%m%d')
                output_file = os.path.join(self.results_dir, f'filtered_{date_str}.csv')
            
            # 转换为DataFrame
            df = pd.DataFrame(matched_stocks)
            
            # 调整列顺序
            columns_order = [
                'code', 'name', 'date', 'close', 'ma', 
                'volume', 'prev_volume', 'volume_ratio'
            ]
            
            # 只保留存在的列
            available_columns = [col for col in columns_order if col in df.columns]
            # 添加其他列
            other_columns = [col for col in df.columns if col not in available_columns]
            final_columns = available_columns + other_columns
            
            df = df[final_columns]
            
            # 重命名列（中文）
            df.rename(columns={
                'code': '股票代码',
                'name': '股票名称',
                'date': '日期',
                'close': '收盘价',
                'ma': f'{self.ma_period}日均线',
                'volume': '成交量',
                'prev_volume': '前日成交量',
                'volume_ratio': '成交量倍数',
                'open': '开盘价',
                'high': '最高价',
                'low': '最低价',
                'change_pct': '涨跌幅'
            }, inplace=True)
            
            # 按成交量倍数降序排序
            if '成交量倍数' in df.columns:
                df = df.sort_values('成交量倍数', ascending=False)
            
            # 保存文件
            if safe_write_csv(df, output_file):
                self.logger.info(f"结果已保存到: {output_file}")
                return True
            else:
                self.logger.error("保存结果失败")
                return False
                
        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")
            return False
    
    def run_filter(self, callback: Callable = None) -> tuple:
        """
        执行完整的筛选流程
        
        Args:
            callback: 进度回调函数
        
        Returns:
            (符合条件的股票列表, 结果文件路径)
        """
        self.logger.info("开始执行股票筛选...")
        
        # 获取股票列表
        stock_list = self.get_stock_list()
        if stock_list is None:
            self.logger.error("无法获取股票列表")
            return [], None
        
        # 筛选股票
        matched_stocks = self.filter_all_stocks(stock_list, callback)
        
        if not matched_stocks:
            self.logger.warning("没有找到符合条件的股票")
            return [], None
        
        # 保存结果
        date_str = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(self.results_dir, f'filtered_{date_str}.csv')
        
        if self.save_results(matched_stocks, output_file):
            return matched_stocks, output_file
        else:
            return matched_stocks, None
    
    def get_history_results(self, days: int = 30) -> List[str]:
        """
        获取历史筛选结果文件列表
        
        Args:
            days: 最近几天
        
        Returns:
            结果文件路径列表
        """
        try:
            if not os.path.exists(self.results_dir):
                return []
            
            result_files = []
            cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
            
            for filename in os.listdir(self.results_dir):
                if not filename.startswith('filtered_') or not filename.endswith('.csv'):
                    continue
                
                file_path = os.path.join(self.results_dir, filename)
                file_time = os.path.getmtime(file_path)
                
                if file_time >= cutoff_date:
                    result_files.append(file_path)
            
            # 按时间倒序排序
            result_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            return result_files
            
        except Exception as e:
            self.logger.error(f"获取历史结果失败: {e}")
            return []
    
    def load_result_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        加载结果文件
        
        Args:
            file_path: 结果文件路径
        
        Returns:
            DataFrame
        """
        return safe_read_csv(file_path)


def main():
    """测试代码"""
    stock_filter = StockFilter()
    
    def progress_callback(current, total, stock_code, matched):
        """进度回调"""
        if current % 100 == 0:
            print(f"进度: {current}/{total}, 当前: {stock_code}, 匹配: {matched}")
    
    # 执行筛选
    print("开始筛选股票...")
    matched_stocks, output_file = stock_filter.run_filter(callback=progress_callback)
    
    print(f"\n筛选完成！")
    print(f"符合条件的股票数量: {len(matched_stocks)}")
    if output_file:
        print(f"结果文件: {output_file}")
    
    # 显示前10只股票
    if matched_stocks:
        print("\n前10只股票:")
        for i, stock in enumerate(matched_stocks[:10], 1):
            print(f"{i}. {stock['code']} {stock['name']} - "
                  f"价格: {stock['close']:.2f}, "
                  f"成交量倍数: {stock['volume_ratio']:.2f}")
    
    # 查看历史结果
    print("\n历史结果文件:")
    history_files = stock_filter.get_history_results(days=30)
    for file_path in history_files:
        print(f"- {os.path.basename(file_path)}")


if __name__ == '__main__':
    main()
