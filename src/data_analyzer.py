"""
数据分析模块
计算技术指标：移动平均线、成交量变化等
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Optional, Tuple, Dict

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, safe_read_csv


class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self, ma_period: int = 120):
        """
        初始化数据分析器
        
        Args:
            ma_period: 移动平均线周期
        """
        self.ma_period = ma_period
        self.logger = setup_logger('DataAnalyzer')
        self.logger.info(f"数据分析器初始化完成，MA周期: {ma_period}")
    
    def calculate_ma(self, df: pd.DataFrame, period: int = None,
                     price_column: str = 'close') -> pd.DataFrame:
        """
        计算移动平均线
        
        Args:
            df: 数据DataFrame
            period: MA周期，如果为None则使用默认值
            price_column: 价格列名
        
        Returns:
            添加了MA列的DataFrame
        """
        if period is None:
            period = self.ma_period
        
        if df is None or df.empty:
            self.logger.warning("数据为空，无法计算MA")
            return df
        
        if price_column not in df.columns:
            self.logger.error(f"列 '{price_column}' 不存在")
            return df
        
        try:
            # 计算移动平均线
            df = df.copy()
            ma_column = f'MA{period}'
            df[ma_column] = df[price_column].rolling(window=period, min_periods=period).mean()
            
            self.logger.debug(f"成功计算 {ma_column}")
            return df
        except Exception as e:
            self.logger.error(f"计算MA失败: {e}")
            return df
    
    def calculate_volume_ratio(self, df: pd.DataFrame,
                               volume_column: str = 'volume') -> pd.DataFrame:
        """
        计算成交量变化倍数（当日成交量/前一日成交量）
        
        Args:
            df: 数据DataFrame
            volume_column: 成交量列名
        
        Returns:
            添加了volume_ratio列的DataFrame
        """
        if df is None or df.empty:
            self.logger.warning("数据为空，无法计算成交量倍数")
            return df
        
        if volume_column not in df.columns:
            self.logger.error(f"列 '{volume_column}' 不存在")
            return df
        
        try:
            df = df.copy()
            # 计算前一日成交量
            df['prev_volume'] = df[volume_column].shift(1)
            # 计算成交量倍数
            df['volume_ratio'] = df[volume_column] / df['prev_volume']
            # 处理除零和无穷大
            df['volume_ratio'] = df['volume_ratio'].replace([np.inf, -np.inf], np.nan)
            
            self.logger.debug("成功计算成交量倍数")
            return df
        except Exception as e:
            self.logger.error(f"计算成交量倍数失败: {e}")
            return df
    
    def analyze_stock(self, df: pd.DataFrame, 
                     ma_period: int = None) -> Optional[pd.DataFrame]:
        """
        对股票数据进行完整分析
        
        Args:
            df: 股票数据DataFrame
            ma_period: MA周期
        
        Returns:
            分析后的DataFrame
        """
        if df is None or df.empty:
            return None
        
        try:
            # 确保数据按日期排序
            df = df.copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 计算移动平均线
            df = self.calculate_ma(df, period=ma_period)
            
            # 计算成交量倍数
            df = self.calculate_volume_ratio(df)
            
            return df
        except Exception as e:
            self.logger.error(f"分析股票数据失败: {e}")
            return None
    
    def check_filter_conditions(self, df: pd.DataFrame,
                               volume_ratio_threshold: float = 5.0,
                               ma_period: int = None) -> Tuple[bool, Optional[Dict]]:
        """
        检查股票是否符合筛选条件
        
        条件：
        1. 最近两天成交量增加5倍以上
        2. 当前价格在MA120均线上方
        
        Args:
            df: 分析后的股票数据
            volume_ratio_threshold: 成交量倍数阈值
            ma_period: MA周期
        
        Returns:
            (是否符合条件, 详细信息字典)
        """
        if df is None or df.empty:
            return False, None
        
        if ma_period is None:
            ma_period = self.ma_period
        
        ma_column = f'MA{ma_period}'
        
        try:
            # 检查必要的列是否存在
            required_columns = ['date', 'close', 'volume', ma_column, 'volume_ratio']
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                self.logger.warning(f"缺少必要的列: {missing}")
                return False, None
            
            # 获取最新的数据（最后一行）
            latest = df.iloc[-1]
            
            # 检查数据是否有效
            if pd.isna(latest[ma_column]) or pd.isna(latest['volume_ratio']):
                self.logger.debug("最新数据包含NaN，不符合条件")
                return False, None
            
            # 检查是否有足够的历史数据
            if len(df) < ma_period:
                self.logger.debug(f"历史数据不足 {ma_period} 天")
                return False, None
            
            # 条件1：成交量倍数 >= 阈值
            volume_condition = latest['volume_ratio'] >= volume_ratio_threshold
            
            # 条件2：当前价格 >= MA
            price_condition = latest['close'] >= latest[ma_column]
            
            # 同时满足两个条件
            if volume_condition and price_condition:
                # 获取前一日数据
                if len(df) >= 2:
                    prev = df.iloc[-2]
                    prev_volume = prev['volume']
                else:
                    prev_volume = latest['prev_volume']
                
                info = {
                    'date': latest['date'].strftime('%Y-%m-%d') if isinstance(latest['date'], pd.Timestamp) else str(latest['date']),
                    'close': float(latest['close']),
                    'ma': float(latest[ma_column]),
                    'volume': float(latest['volume']),
                    'prev_volume': float(prev_volume),
                    'volume_ratio': float(latest['volume_ratio']),
                    'open': float(latest['open']) if 'open' in latest else None,
                    'high': float(latest['high']) if 'high' in latest else None,
                    'low': float(latest['low']) if 'low' in latest else None,
                    'change_pct': float(latest['change_pct']) if 'change_pct' in latest else None
                }
                
                self.logger.debug(f"符合条件: 价格={info['close']:.2f}, MA={info['ma']:.2f}, "
                                f"成交量倍数={info['volume_ratio']:.2f}")
                return True, info
            else:
                self.logger.debug(f"不符合条件: 成交量倍数={latest['volume_ratio']:.2f}, "
                                f"价格={latest['close']:.2f}, MA={latest[ma_column]:.2f}")
                return False, None
                
        except Exception as e:
            self.logger.error(f"检查筛选条件失败: {e}")
            return False, None
    
    def analyze_from_file(self, file_path: str,
                         volume_ratio_threshold: float = 5.0,
                         ma_period: int = None) -> Tuple[bool, Optional[Dict]]:
        """
        从文件读取数据并分析
        
        Args:
            file_path: 数据文件路径
            volume_ratio_threshold: 成交量倍数阈值
            ma_period: MA周期
        
        Returns:
            (是否符合条件, 详细信息字典)
        """
        try:
            # 读取数据
            df = safe_read_csv(file_path)
            if df is None or df.empty:
                return False, None
            
            # 分析数据
            df = self.analyze_stock(df, ma_period=ma_period)
            if df is None:
                return False, None
            
            # 检查条件
            return self.check_filter_conditions(df, volume_ratio_threshold, ma_period)
            
        except Exception as e:
            self.logger.error(f"从文件分析失败 {file_path}: {e}")
            return False, None
    
    def get_stock_summary(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        获取股票数据摘要
        
        Args:
            df: 股票数据
        
        Returns:
            摘要信息字典
        """
        if df is None or df.empty:
            return None
        
        try:
            latest = df.iloc[-1]
            summary = {
                'total_days': len(df),
                'latest_date': latest['date'].strftime('%Y-%m-%d') if isinstance(latest['date'], pd.Timestamp) else str(latest['date']),
                'latest_close': float(latest['close']),
                'latest_volume': float(latest['volume']),
                'avg_volume': float(df['volume'].mean()),
                'max_price': float(df['close'].max()),
                'min_price': float(df['close'].min())
            }
            
            # 添加MA信息（如果存在）
            for period in [5, 10, 20, 60, 120]:
                ma_col = f'MA{period}'
                if ma_col in df.columns and not pd.isna(latest[ma_col]):
                    summary[f'ma{period}'] = float(latest[ma_col])
            
            return summary
        except Exception as e:
            self.logger.error(f"获取摘要失败: {e}")
            return None


def main():
    """测试代码"""
    analyzer = DataAnalyzer(ma_period=120)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=150, freq='D')
    test_data = pd.DataFrame({
        'date': dates,
        'open': np.random.uniform(10, 15, 150),
        'close': np.random.uniform(10, 15, 150),
        'high': np.random.uniform(12, 16, 150),
        'low': np.random.uniform(8, 12, 150),
        'volume': np.random.uniform(1000000, 5000000, 150)
    })
    
    # 让最后一天的成交量是前一天的6倍
    test_data.loc[test_data.index[-1], 'volume'] = test_data.loc[test_data.index[-2], 'volume'] * 6
    
    # 让最后一天的价格高于平均值
    test_data.loc[test_data.index[-1], 'close'] = 14.5
    
    print("测试数据:")
    print(test_data.tail())
    
    # 分析数据
    print("\n分析数据...")
    analyzed_df = analyzer.analyze_stock(test_data)
    print(analyzed_df.tail())
    
    # 检查筛选条件
    print("\n检查筛选条件...")
    is_match, info = analyzer.check_filter_conditions(analyzed_df, volume_ratio_threshold=5.0)
    print(f"是否符合条件: {is_match}")
    if info:
        print(f"详细信息: {info}")
    
    # 获取摘要
    print("\n获取摘要...")
    summary = analyzer.get_stock_summary(analyzed_df)
    print(f"摘要信息: {summary}")


if __name__ == '__main__':
    main()
