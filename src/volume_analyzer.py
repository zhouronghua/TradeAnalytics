"""
成交量分析模块
支持批处理运行，自动更新数据并推送分析结果
"""

import pandas as pd
import os
import glob
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, Config, ensure_dir, is_data_up_to_date, get_last_trading_day
from src.data_downloader import DataDownloader
from src.notification import NotificationService
from src.email_sender import EmailSender

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


def analyze_volume_surge(csv_files: List[str], progress_callback=None,
                         volume_avg_days: int = 5,
                         volume_ratio_threshold: float = 5.0,
                         ma_period: int = 5,
                         max_days_old: int = 2) -> pd.DataFrame:
    """
    分析成交量暴涨股票
    规则：当天成交量 >= 前5日平均成交量的5倍，且收盘价突破MA5日均线
    
    Args:
        csv_files: CSV文件路径列表
        progress_callback: 进度回调函数
        volume_avg_days: 均量计算天数
        volume_ratio_threshold: 量比阈值
        ma_period: 均线周期（默认MA5）
        max_days_old: 最多保留几天前的数据（默认2天，即当天或前一天）
    
    Returns:
        分析结果DataFrame
    """
    all_results = []
    processed = 0
    total = len(csv_files)
    
    for file_path in csv_files:
        results = analyze_stock_flexible(
            file_path,
            volume_avg_days=volume_avg_days,
            volume_ratio_threshold=volume_ratio_threshold,
            ma_period=ma_period,
        )
        
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
    
    # 重要：过滤掉数据日期过旧的股票
    # 只保留最近 max_days_old 天的数据（避免把几个月前的数据当作最新数据）
    today = pd.Timestamp.now().normalize()
    cutoff_date = today - pd.Timedelta(days=max_days_old)
    
    results_df = results_df[results_df['date'] >= cutoff_date]
    
    if results_df.empty:
        return pd.DataFrame()
    
    # 转换回字符串格式并按成交量倍数排序
    results_df['date'] = results_df['date'].dt.strftime('%Y-%m-%d')
    results_df = results_df.sort_values('volume_ratio', ascending=False)
    
    return results_df


def analyze_stock_flexible(file_path: str, recent_days: int = 30,
                           volume_avg_days: int = 5,
                           volume_ratio_threshold: float = 5.0,
                           ma_period: int = 5) -> Optional[List[Dict]]:
    """
    灵活分析单只股票
    规则：检查最近N天的数据，找出成交量 >= 前5日平均成交量5倍的日期，且收盘价突破MA5
    
    注意：BaoStock是T+1数据，当天的数据要第二天才能获取
    
    Args:
        file_path: CSV文件路径
        recent_days: 检查最近N天的数据，默认30天
        volume_avg_days: 均量计算天数
        volume_ratio_threshold: 量比阈值
        ma_period: 均线周期
    
    Returns:
        符合条件的记录列表
    """
    try:
        df = pd.read_csv(file_path, dtype={'code': str})
        
        min_days = max(ma_period, volume_avg_days) + 1
        if len(df) < min_days:
            return None
        
        # 确保日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 记录最新数据日期（用于调试）
        latest_date = df['date'].max()
        
        df['ma'] = df['close'].rolling(window=ma_period).mean()
        
        # 获取最近N天的数据（扩大分析范围）
        recent_data = df.tail(min(recent_days, len(df))).reset_index(drop=True)
        
        results = []
        
        # 检查每一天（需要至少 volume_avg_days 天历史 + 前一日用于判断突破）
        start_idx = max(volume_avg_days, ma_period)
        for i in range(start_idx, len(recent_data)):
            current = recent_data.iloc[i]
            previous = recent_data.iloc[i - 1]
            
            if pd.isna(current['ma']) or pd.isna(previous['ma']):
                continue
            
            prev_days = recent_data.iloc[i - volume_avg_days:i]
            avg_volume = prev_days['volume'].mean()
            
            volume_ratio = current['volume'] / avg_volume if avg_volume > 0 else 0
            ma_breakout = (
                previous['close'] <= previous['ma']
                and current['close'] > current['ma']
            )
            
            if volume_ratio >= volume_ratio_threshold and ma_breakout:
                stock_code = os.path.basename(file_path).replace('.csv', '')
                stock_name = get_stock_name(stock_code)
                
                results.append({
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'date': current['date'].strftime('%Y-%m-%d'),
                    'close': current['close'],
                    'ma': current['ma'],
                    'ma_period': ma_period,
                    'volume': current['volume'],
                    'avg_5day_volume': int(avg_volume),
                    'volume_ratio': volume_ratio,
                    'price_above_ma': ((current['close'] - current['ma']) / current['ma'] * 100),
                    'data_latest_date': latest_date.strftime('%Y-%m-%d')
                })
        
        return results
    
    except Exception as e:
        return None


class VolumeAnalyzer:
    """成交量分析器（支持批处理）"""
    
    def __init__(self, config_file: str = 'config/config.ini'):
        """
        初始化成交量分析器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = Config(config_file)
        self.logger = setup_logger('VolumeAnalyzer')
        
        # 读取配置
        self.daily_dir = self.config.get('Paths', 'daily_dir', fallback='./data/daily')
        self.stocks_dir = self.config.get('Paths', 'stocks_dir', fallback='./data/stocks')
        self.results_dir = self.config.get('Paths', 'results_dir', fallback='./data/results')
        self.ma_period = self.config.getint('Analysis', 'ma_period', fallback=5)
        self.volume_ratio = self.config.getfloat('Analysis', 'volume_ratio_threshold', fallback=5.0)
        self.volume_avg_days = self.config.getint('Analysis', 'volume_avg_days', fallback=5)
        
        # 确保目录存在
        ensure_dir(self.results_dir)
        
        # 初始化组件
        self.downloader = DataDownloader(config_file)
        self.notifier = NotificationService(config_file)
        self.email_sender = EmailSender(config_file)
        
        self.logger.info(
            f"成交量分析器初始化完成 (MA{self.ma_period}突破, "
            f"前{self.volume_avg_days}日均量>={self.volume_ratio}倍)"
        )
    
    def run_batch_analysis(self, update_data: bool = True, 
                          send_email: bool = True, 
                          send_notification: bool = True) -> bool:
        """
        运行批处理分析
        
        Args:
            update_data: 是否更新数据
            send_email: 是否发送邮件
            send_notification: 是否发送方糖推送
        
        Returns:
            是否成功
        """
        try:
            self.logger.info("="*60)
            self.logger.info("开始批处理成交量分析")
            self.logger.info("="*60)
            
            analysis_date = datetime.now().strftime('%Y-%m-%d')
            
            # 步骤1: 更新数据
            if update_data:
                self.logger.info("\n[步骤1/3] 更新交易数据...")
                analysis_ref = get_last_trading_day(datetime.now())
                up_to_date, status_msg = is_data_up_to_date(self.daily_dir, analysis_ref)
                if up_to_date:
                    self.logger.info(f"跳过数据更新: {status_msg}")
                else:
                    self.logger.info(status_msg)
                    try:
                        stock_list = self.downloader.download_stock_list()
                        if stock_list is None:
                            self.logger.error("无法获取股票列表")
                            self.logger.info("将使用现有数据继续分析...")
                        else:
                            self.logger.info(f"获取到 {len(stock_list)} 只股票")
                            
                            success_count, fail_count = self.downloader.download_all_stocks(stock_list)
                            total = success_count + fail_count
                            
                            if fail_count > 0:
                                self.logger.warning(f"数据更新部分失败: 总计{total}, 成功{success_count}, 失败{fail_count}")
                            else:
                                self.logger.info(f"数据更新成功: 总计{total}, 成功{success_count}")
                    except Exception as e:
                        self.logger.error(f"数据更新失败: {e}")
                        self.logger.info("将使用现有数据继续分析...")
            else:
                self.logger.info("\n[步骤1/3] 跳过数据更新（使用现有数据）")
            
            # 步骤2: 执行成交量分析
            self.logger.info("\n[步骤2/3] 分析成交量暴涨股票...")
            
            # 检查数据目录（日线数据保存在 daily_dir，与 DataDownloader 一致）
            if not os.path.exists(self.daily_dir):
                self.logger.error(f"数据目录不存在: {self.daily_dir}")
                self.logger.error("请先运行数据下载或使用 --no-update 参数（需先有数据）")
                return False
            
            # 获取所有股票CSV文件
            csv_files = glob.glob(os.path.join(self.daily_dir, '*.csv'))
            
            if not csv_files:
                self.logger.error(f"未找到股票数据文件: {self.daily_dir}")
                self.logger.error("可能原因:")
                self.logger.error("  1. 首次运行尚未下载数据")
                self.logger.error("  2. 数据下载失败")
                self.logger.error("  3. 数据目录配置错误")
                self.logger.error("\n解决方法:")
                self.logger.error("  - 运行完整下载: python src/volume_analyzer.py")
                self.logger.error("  - 或手动下载数据: python -c \"from src.data_downloader import DataDownloader; d=DataDownloader(); d.download_all_stocks()\"")
                return False
            
            self.logger.info(f"找到 {len(csv_files)} 个股票数据文件")
            
            # 执行分析（只保留最近2天的数据）
            results_df = analyze_volume_surge(
                csv_files,
                volume_avg_days=self.volume_avg_days,
                volume_ratio_threshold=self.volume_ratio,
                ma_period=self.ma_period,
                max_days_old=2,  # 只保留最近2天的数据
            )
            
            if results_df.empty:
                self.logger.info("未找到符合条件的股票（仅统计最近2天的数据）")
                self.logger.info("注意：如果数据未更新，不会推送历史数据")
                matched_count = 0
            else:
                matched_count = len(results_df)
                self.logger.info(f"找到 {matched_count} 只符合条件的股票（最近2天）")
                
                # 显示数据日期范围
                dates = pd.to_datetime(results_df['date'])
                self.logger.info(f"数据日期范围: {dates.min().strftime('%Y-%m-%d')} 至 {dates.max().strftime('%Y-%m-%d')}")
                
                # 保存结果
                output_file = os.path.join(
                    self.results_dir, 
                    f"volume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
                results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"结果已保存: {output_file}")
            
            # 步骤3: 发送通知
            self.logger.info("\n[步骤3/3] 发送分析结果...")
            
            # 准备推送数据
            matched_stocks = []
            if not results_df.empty:
                for _, row in results_df.iterrows():
                    matched_stocks.append({
                        'code': row['stock_code'],
                        'name': row['stock_name'],
                        'date': row['date'],
                        'close': row['close'],
                        'ma': row['ma'],
                        'volume_ratio': row['volume_ratio']
                    })
            
            # 发送邮件
            if send_email and self.email_sender.enabled:
                try:
                    if matched_stocks:
                        strategy_meta = {
                            'ma_period': self.ma_period,
                            'volume_ratio_threshold': self.volume_ratio,
                            'from_validated': False
                        }
                        email_success = self.email_sender.send_volume_ma_screening_report(
                            matched_stocks, analysis_date, strategy_meta
                        )
                        if email_success:
                            self.logger.info("邮件发送成功")
                        else:
                            self.logger.warning("邮件发送失败")
                    else:
                        strategy_meta = {
                            'ma_period': self.ma_period,
                            'volume_ratio_threshold': self.volume_ratio,
                            'from_validated': False
                        }
                        self.email_sender.send_volume_ma_screening_empty(
                            analysis_date, strategy_meta
                        )
                        self.logger.info("已发送空结果邮件")
                except Exception as e:
                    self.logger.error(f"邮件发送异常: {e}")
            
            # 发送方糖推送
            if send_notification and self.notifier.enabled:
                try:
                    strategy_meta = {
                        'ma_period': self.ma_period,
                        'volume_ratio_threshold': self.volume_ratio,
                        'from_validated': False
                    }
                    
                    if matched_stocks:
                        # 有匹配的股票，发送正常通知
                        notify_success = self.notifier.send_analysis_result(
                            matched_stocks, analysis_date, 
                            include_history=True, 
                            strategy_meta=strategy_meta
                        )
                        if notify_success:
                            self.logger.info("方糖推送成功")
                        else:
                            self.logger.warning("方糖推送失败")
                    else:
                        # 没有匹配的股票，发送空通知
                        notify_success = self.notifier.send_empty_analysis_result(
                            analysis_date, strategy_meta
                        )
                        if notify_success:
                            self.logger.info("已发送空结果方糖推送")
                        else:
                            self.logger.warning("空结果方糖推送失败")
                except Exception as e:
                    self.logger.error(f"方糖推送异常: {e}")
            
            self.logger.info("\n" + "="*60)
            self.logger.info(f"批处理分析完成! 找到 {matched_count} 只符合条件的股票")
            self.logger.info("="*60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"批处理分析异常: {e}", exc_info=True)
            return False


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description='成交量分析批处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 完整运行（更新数据+分析+推送）
  python src/volume_analyzer.py
  
  # 只分析，不更新数据
  python src/volume_analyzer.py --no-update
  
  # 只分析，不发送任何通知
  python src/volume_analyzer.py --no-email --no-notification
  
  # 指定配置文件
  python src/volume_analyzer.py --config config/custom.ini

适用场景:
  - crontab定时任务
  - 手动批处理分析
  - 数据更新后的自动分析
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/config.ini',
        help='配置文件路径 (默认: config/config.ini)'
    )
    parser.add_argument(
        '--no-update',
        action='store_true',
        help='不更新数据，使用现有数据'
    )
    parser.add_argument(
        '--no-email',
        action='store_true',
        help='不发送邮件'
    )
    parser.add_argument(
        '--no-notification',
        action='store_true',
        help='不发送方糖推送'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    args = parser.parse_args()
    
    # 检查配置文件
    if not os.path.exists(args.config):
        print(f"错误: 配置文件不存在: {args.config}")
        print(f"请复制 config/config.ini.example 为 {args.config} 并配置")
        return 1
    
    try:
        # 创建分析器
        analyzer = VolumeAnalyzer(args.config)
        
        # 运行批处理分析
        success = analyzer.run_batch_analysis(
            update_data=not args.no_update,
            send_email=not args.no_email,
            send_notification=not args.no_notification
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
        return 130
    except Exception as e:
        print(f"运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
