"""
工具函数模块
提供日期处理、文件操作、日志配置等通用功能
"""

import os
import logging
import configparser
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = 'config/config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        
        if os.path.exists(config_file):
            self.config.read(config_file, encoding='utf-8')
        else:
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
    
    def get(self, section: str, key: str, fallback=None):
        """获取配置项"""
        return self.config.get(section, key, fallback=fallback)
    
    def getint(self, section: str, key: str, fallback=None):
        """获取整数配置项"""
        return self.config.getint(section, key, fallback=fallback)
    
    def getfloat(self, section: str, key: str, fallback=None):
        """获取浮点数配置项"""
        return self.config.getfloat(section, key, fallback=fallback)
    
    def getboolean(self, section: str, key: str, fallback=None):
        """获取布尔配置项"""
        return self.config.getboolean(section, key, fallback=fallback)


def setup_logger(name: str, log_dir: str = 'logs', level=logging.INFO) -> logging.Logger:
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志目录
        level: 日志级别
    
    Returns:
        配置好的日志记录器
    """
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建文件处理器（按日期）
    log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def is_trading_day(date: datetime) -> bool:
    """
    判断是否为交易日
    简单实现：排除周末，实际应使用交易日历API
    
    Args:
        date: 日期对象
    
    Returns:
        是否为交易日
    """
    # 周末不是交易日
    if date.weekday() >= 5:
        return False
    
    # 这里简化处理，实际应该调用AkShare的交易日历接口
    # tool_trade_date_hist_sina() 获取历史交易日
    return True


def get_recent_trading_days(n: int = 2) -> List[str]:
    """
    获取最近N个交易日
    
    Args:
        n: 天数
    
    Returns:
        交易日列表，格式：YYYYMMDD
    """
    trading_days = []
    current_date = datetime.now()
    
    while len(trading_days) < n:
        if is_trading_day(current_date):
            trading_days.append(current_date.strftime('%Y%m%d'))
        current_date -= timedelta(days=1)
    
    return list(reversed(trading_days))


def format_date(date_str: str, input_format: str = '%Y%m%d', output_format: str = '%Y-%m-%d') -> str:
    """
    日期格式转换
    
    Args:
        date_str: 输入日期字符串
        input_format: 输入格式
        output_format: 输出格式
    
    Returns:
        转换后的日期字符串
    """
    try:
        date_obj = datetime.strptime(date_str, input_format)
        return date_obj.strftime(output_format)
    except Exception as e:
        logging.error(f"日期格式转换失败: {date_str}, {e}")
        return date_str


def safe_read_csv(file_path: str, **kwargs) -> Optional[pd.DataFrame]:
    """
    安全读取CSV文件
    
    Args:
        file_path: 文件路径
        **kwargs: pandas.read_csv的其他参数
    
    Returns:
        DataFrame或None
    """
    try:
        if not os.path.exists(file_path):
            logging.warning(f"文件不存在: {file_path}")
            return None
        
        df = pd.read_csv(file_path, **kwargs)
        return df
    except Exception as e:
        logging.error(f"读取CSV文件失败: {file_path}, {e}")
        return None


def safe_write_csv(df: pd.DataFrame, file_path: str, **kwargs) -> bool:
    """
    安全写入CSV文件
    
    Args:
        df: DataFrame
        file_path: 文件路径
        **kwargs: pandas.to_csv的其他参数
    
    Returns:
        是否成功
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        df.to_csv(file_path, index=False, encoding='utf-8-sig', **kwargs)
        return True
    except Exception as e:
        logging.error(f"写入CSV文件失败: {file_path}, {e}")
        return False


def get_stock_data_path(stock_code: str, data_dir: str = 'data/daily') -> str:
    """
    获取股票数据文件路径
    
    Args:
        stock_code: 股票代码
        data_dir: 数据目录
    
    Returns:
        文件路径
    """
    return os.path.join(data_dir, f"{stock_code}.csv")


def format_number(num: float, precision: int = 2) -> str:
    """
    格式化数字
    
    Args:
        num: 数字
        precision: 小数位数
    
    Returns:
        格式化后的字符串
    """
    if num >= 1e8:
        return f"{num / 1e8:.{precision}f}亿"
    elif num >= 1e4:
        return f"{num / 1e4:.{precision}f}万"
    else:
        return f"{num:.{precision}f}"


def clean_old_logs(log_dir: str = 'logs', keep_days: int = 30):
    """
    清理旧日志文件
    
    Args:
        log_dir: 日志目录
        keep_days: 保留天数
    """
    try:
        if not os.path.exists(log_dir):
            return
        
        current_time = datetime.now()
        for filename in os.listdir(log_dir):
            if not filename.endswith('.log'):
                continue
            
            file_path = os.path.join(log_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if (current_time - file_time).days > keep_days:
                os.remove(file_path)
                logging.info(f"删除旧日志文件: {filename}")
    except Exception as e:
        logging.error(f"清理日志文件失败: {e}")


def ensure_dir(directory: str):
    """
    确保目录存在
    
    Args:
        directory: 目录路径
    """
    os.makedirs(directory, exist_ok=True)


if __name__ == '__main__':
    # 测试代码
    logger = setup_logger('test')
    logger.info("日志系统测试")
    
    print("最近2个交易日:", get_recent_trading_days(2))
    print("格式化数字:", format_number(123456789))
    print("格式化日期:", format_date('20240206'))
