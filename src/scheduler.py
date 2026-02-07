"""
定时任务模块
自动执行股票数据下载和分析
"""

import schedule
import time
import threading
import os
import sys
from datetime import datetime
from typing import Callable, Optional

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, Config, is_trading_day
from src.data_downloader import DataDownloader
from src.stock_filter import StockFilter


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config_file: str = 'config/config.ini'):
        """
        初始化任务调度器
        
        Args:
            config_file: 配置文件路径
        """
        self.config = Config(config_file)
        self.logger = setup_logger('TaskScheduler')
        
        # 读取配置
        self.enabled = self.config.getboolean('Scheduler', 'enabled', fallback=True)
        self.run_time = self.config.get('Scheduler', 'run_time', fallback='15:30')
        self.weekdays_only = self.config.getboolean('Scheduler', 'weekdays_only', fallback=True)
        
        # 初始化组件
        self.downloader = DataDownloader(config_file)
        self.filter = StockFilter(config_file)
        
        # 状态管理
        self.is_running = False
        self.last_run_time = None
        self.next_run_time = None
        self.scheduler_thread = None
        self.stop_flag = False
        
        # 回调函数
        self.progress_callback = None
        self.complete_callback = None
        
        self.logger.info(f"任务调度器初始化完成 (启用: {self.enabled}, 执行时间: {self.run_time})")
    
    def set_progress_callback(self, callback: Callable):
        """
        设置进度回调函数
        
        Args:
            callback: 回调函数 (stage, current, total, message)
        """
        self.progress_callback = callback
    
    def set_complete_callback(self, callback: Callable):
        """
        设置完成回调函数
        
        Args:
            callback: 回调函数 (success, message, matched_count)
        """
        self.complete_callback = callback
    
    def _notify_progress(self, stage: str, current: int, total: int, message: str):
        """通知进度"""
        if self.progress_callback:
            try:
                self.progress_callback(stage, current, total, message)
            except Exception as e:
                self.logger.error(f"进度回调异常: {e}")
    
    def _notify_complete(self, success: bool, message: str, matched_count: int = 0):
        """通知完成"""
        if self.complete_callback:
            try:
                self.complete_callback(success, message, matched_count)
            except Exception as e:
                self.logger.error(f"完成回调异常: {e}")
    
    def daily_analysis_task(self):
        """
        每日分析任务
        执行流程：
        1. 下载/更新股票列表
        2. 下载最新交易数据
        3. 检查是否为交易日
        4. 执行股票筛选
        5. 保存结果
        """
        if self.is_running:
            self.logger.warning("任务已在运行中，跳过本次执行")
            return
        
        self.is_running = True
        self.last_run_time = datetime.now()
        
        try:
            self.logger.info("=" * 50)
            self.logger.info("开始执行每日分析任务")
            self.logger.info(f"执行时间: {self.last_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("=" * 50)
                        
            # 1. 下载股票列表
            self.logger.info("步骤1: 下载股票列表...")
            self._notify_progress('下载股票列表', 0, 1, '正在获取股票列表...')
            
            stock_list = self.downloader.download_stock_list(force_update=True)
            if stock_list is None or stock_list.empty:
                message = "获取股票列表失败"
                self.logger.error(message)
                self._notify_complete(False, message, 0)
                return
            
            stock_count = len(stock_list)
            self.logger.info(f"获取到 {stock_count} 只股票")
            self._notify_progress('下载股票列表', 1, 1, f'已获取 {stock_count} 只股票')
            
            # 2. 下载股票数据
            self.logger.info("步骤2: 下载股票数据...")
            
            def download_progress(current, total, stock_code, success):
                """下载进度回调"""
                if current % 50 == 0:
                    self._notify_progress(
                        '下载股票数据',
                        current,
                        total,
                        f'已下载 {current}/{total} 只股票 ({stock_code})'
                    )
            
            success_count, fail_count = self.downloader.download_all_stocks(
                stock_list,
                callback=download_progress
            )
            
            self.logger.info(f"下载完成: 成功 {success_count}, 失败 {fail_count}")
            self._notify_progress('下载股票数据', success_count, stock_count, 
                                f'下载完成: {success_count}/{stock_count}')
            
            # 3. 检查是否为交易日
            if self.weekdays_only and not is_trading_day(datetime.now()):
                message = "今天不是交易日，跳过任务"
                self.logger.info(message)
                self._notify_complete(True, message, 0)
                return

            # 4. 执行筛选
            self.logger.info("步骤3: 执行股票筛选...")
            
            def filter_progress(current, total, stock_code, matched):
                """筛选进度回调"""
                if current % 50 == 0:
                    self._notify_progress(
                        '筛选股票',
                        current,
                        total,
                        f'已筛选 {current}/{total} 只股票 ({stock_code})'
                    )
            
            matched_stocks, output_file = self.filter.run_filter(callback=filter_progress)
            
            matched_count = len(matched_stocks)
            self.logger.info(f"筛选完成: 找到 {matched_count} 只符合条件的股票")
            self._notify_progress('筛选股票', stock_count, stock_count, 
                                f'筛选完成: {matched_count} 只符合条件')
            
            # 5. 完成
            if output_file:
                message = f"任务完成！找到 {matched_count} 只符合条件的股票，结果已保存到 {output_file}"
            else:
                message = f"任务完成！找到 {matched_count} 只符合条件的股票"
            
            self.logger.info(message)
            self._notify_complete(True, message, matched_count)
            
            self.logger.info("=" * 50)
            self.logger.info("每日分析任务执行完成")
            self.logger.info("=" * 50)
            
        except Exception as e:
            error_msg = f"任务执行失败: {e}"
            self.logger.error(error_msg, exc_info=True)
            self._notify_complete(False, error_msg, 0)
        
        finally:
            self.is_running = False
    
    def run_once(self):
        """立即执行一次任务"""
        self.logger.info("手动触发任务执行")
        self.daily_analysis_task()
    
    def _schedule_loop(self):
        """调度循环（在独立线程中运行）"""
        self.logger.info("调度循环启动")
        
        while not self.stop_flag:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"调度循环异常: {e}")
    
    def start(self):
        """启动定时任务"""
        if not self.enabled:
            self.logger.info("定时任务未启用")
            return
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.logger.warning("定时任务已在运行")
            return
        
        # 清空之前的调度
        schedule.clear()
        
        # 设置每日任务
        schedule.every().day.at(self.run_time).do(self.daily_analysis_task)
        
        # 计算下次执行时间
        self._update_next_run_time()
        
        # 启动调度线程
        self.stop_flag = False
        self.scheduler_thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info(f"定时任务已启动，将在每天 {self.run_time} 执行")
        self.logger.info(f"下次执行时间: {self.next_run_time}")
    
    def stop(self):
        """停止定时任务"""
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            self.logger.info("定时任务未运行")
            return
        
        self.logger.info("正在停止定时任务...")
        self.stop_flag = True
        
        # 等待线程结束（最多5秒）
        self.scheduler_thread.join(timeout=5)
        
        # 清空调度
        schedule.clear()
        
        self.logger.info("定时任务已停止")
    
    def _update_next_run_time(self):
        """更新下次执行时间"""
        try:
            jobs = schedule.get_jobs()
            if jobs:
                self.next_run_time = jobs[0].next_run
            else:
                self.next_run_time = None
        except Exception as e:
            self.logger.error(f"更新下次执行时间失败: {e}")
            self.next_run_time = None
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        获取下次执行时间
        
        Returns:
            下次执行时间
        """
        self._update_next_run_time()
        return self.next_run_time
    
    def get_last_run_time(self) -> Optional[datetime]:
        """
        获取上次执行时间
        
        Returns:
            上次执行时间
        """
        return self.last_run_time
    
    def is_task_running(self) -> bool:
        """
        检查任务是否正在运行
        
        Returns:
            是否正在运行
        """
        return self.is_running
    
    def update_schedule_time(self, run_time: str):
        """
        更新执行时间
        
        Args:
            run_time: 执行时间，格式：HH:MM
        """
        self.run_time = run_time
        
        # 如果已启动，重新启动以应用新时间
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.stop()
            self.start()
            self.logger.info(f"执行时间已更新为: {run_time}")


def main():
    """测试代码"""
    scheduler = TaskScheduler()
    
    def progress_callback(stage, current, total, message):
        """进度回调"""
        print(f"[{stage}] {current}/{total} - {message}")
    
    def complete_callback(success, message, matched_count):
        """完成回调"""
        if success:
            print(f"任务完成: {message}")
        else:
            print(f"任务失败: {message}")
    
    scheduler.set_progress_callback(progress_callback)
    scheduler.set_complete_callback(complete_callback)
    
    # 测试立即执行
    print("立即执行任务...")
    scheduler.run_once()
    
    # 测试定时任务
    print("\n启动定时任务...")
    scheduler.start()
    print(f"下次执行时间: {scheduler.get_next_run_time()}")
    
    # 运行一段时间
    try:
        print("定时任务运行中，按 Ctrl+C 停止...")
        while True:
            time.sleep(60)
            next_run = scheduler.get_next_run_time()
            if next_run:
                print(f"下次执行时间: {next_run}")
    except KeyboardInterrupt:
        print("\n停止定时任务...")
        scheduler.stop()


if __name__ == '__main__':
    main()
