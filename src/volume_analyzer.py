"""
成交量分析模块
"""

import pandas as pd
import os
import glob
from typing import List, Dict, Optional

# 全局股票列表缓存
_stock_list_cache = None


def load_stock_list() -> Optional[pd.DataFrame]:
    """加载股票列表（带缓存）"""
    global _stock_list_cache
    
    if _stock_list_cache is not None:
        return _stock_list_cache
    
    stock_list_file = './data/stocks/stock_list.csv'
    if os.path.exists(stock_list_file):
        try:
            _stock_list_cache = pd.read_csv(stock_list_file, dtype={'code': str})
            return _stock_list_cache
        except Exception as e:
            print(f"加载股票列表失败: {e}")
            return None
    return None


def get_stock_name(stock_code: str) -> str:
    """根据股票代码获取股票名称"""
    stock_list = load_stock_list()
    
    if stock_list is None:
        return stock_code
    
    # 确保stock_code是6位字符串
    stock_code = str(stock_code).zfill(6)
    
    # 查找股票名称
    match = stock_list[stock_list['code'] == stock_code]
    if not match.empty and 'name' in match.columns:
        name = match.iloc[0]['name']
        # 如果name不为空且不等于code，返回name
        if pd.notna(name) and str(name) != stock_code:
            return str(name)
    
    return stock_code


def analyze_volume_surge(csv_files: List[str], progress_callback=None) -> pd.DataFrame:
    """
    分析成交量暴涨股票
    规则：当天成交量是前7天平均成交量的5倍以上，且收盘价在均线之上
    
    Args:
        csv_files: CSV文件路径列表
        progress_callback: 进度回调函数
    
    Returns:
        分析结果DataFrame
    """
    all_results = []
    processed = 0
    total = len(csv_files)
    
    for file_path in csv_files:
        results = analyze_stock_flexible(file_path)
        
        if results:
            all_results.extend(results)
        
        processed += 1
        
        # 进度回调 - 每处理100个文件更新一次
        if progress_callback and processed % 100 == 0:
            message = f"已处理: {processed}/{total}, 找到: {len(all_results)} 只"
            progress_callback(processed, total, message)
    
    # 最后一次更新进度
    if progress_callback:
        message = f"分析完成: {processed}/{total}, 找到: {len(all_results)} 只"
        progress_callback(processed, total, message)
    
    if not all_results:
        return pd.DataFrame()
    
    # 转换为DataFrame
    results_df = pd.DataFrame(all_results)
    
    # 对于同一只股票，只保留最新日期的记录
    results_df['date'] = pd.to_datetime(results_df['date'])
    results_df = results_df.sort_values('date', ascending=False)
    results_df = results_df.drop_duplicates(subset='stock_code', keep='first')
    
    # 转换回字符串格式并按成交量倍数排序
    results_df['date'] = results_df['date'].dt.strftime('%Y-%m-%d')
    results_df = results_df.sort_values('volume_ratio', ascending=False)
    
    return results_df


def analyze_stock_flexible(file_path: str, recent_days: int = 30) -> Optional[List[Dict]]:
    """
    灵活分析单只股票
    规则：检查最近N天的数据，找出成交量 >= 前7天平均成交量5倍的日期，且收盘价 > 均线
    
    注意：BaoStock是T+1数据，当天的数据要第二天才能获取
    
    Args:
        file_path: CSV文件路径
        recent_days: 检查最近N天的数据，默认30天
    
    Returns:
        符合条件的记录列表
    """
    try:
        df = pd.read_csv(file_path, dtype={'code': str})
        
        if len(df) < 10:
            return None
        
        # 确保日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 记录最新数据日期（用于调试）
        latest_date = df['date'].max()
        
        # 计算能计算的均线
        if len(df) >= 120:
            ma_period = 120
        elif len(df) >= 60:
            ma_period = 60
        elif len(df) >= 30:
            ma_period = 30
        else:
            ma_period = 10
        
        df['ma'] = df['close'].rolling(window=ma_period).mean()
        
        # 获取最近N天的数据（扩大分析范围）
        recent_data = df.tail(min(recent_days, len(df)))
        
        results = []
        
        # 检查每一天（需要至少8天数据：当天 + 前7天）
        for i in range(7, len(recent_data)):
            current = recent_data.iloc[i]
            
            # 跳过MA为空的数据
            if pd.isna(current['ma']):
                continue
            
            # 计算前7天的平均成交量
            prev_7_days = recent_data.iloc[i-7:i]
            avg_7day_volume = prev_7_days['volume'].mean()
            
            # 检查条件：当天成交量是前7天平均成交量的5倍以上
            volume_ratio = current['volume'] / avg_7day_volume if avg_7day_volume > 0 else 0
            
            if volume_ratio >= 5.0 and current['close'] > current['ma']:
                stock_code = os.path.basename(file_path).replace('.csv', '')
                stock_name = get_stock_name(stock_code)  # 从股票列表中获取真实名称
                
                results.append({
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'date': current['date'].strftime('%Y-%m-%d'),
                    'close': current['close'],
                    'ma': current['ma'],
                    'ma_period': ma_period,
                    'volume': current['volume'],
                    'avg_7day_volume': int(avg_7day_volume),
                    'volume_ratio': volume_ratio,
                    'price_above_ma': ((current['close'] - current['ma']) / current['ma'] * 100),
                    'data_latest_date': latest_date.strftime('%Y-%m-%d')  # 添加最新数据日期
                })
        
        return results
    
    except Exception as e:
        return None
