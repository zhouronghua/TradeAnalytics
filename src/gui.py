"""
GUI界面模块
使用Tkinter构建桌面应用界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import os
import sys
from datetime import datetime
from typing import Optional
import pandas as pd
import glob
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import Config, safe_read_csv, format_number
from src.scheduler import TaskScheduler
from src.data_downloader import DataDownloader
from src.stock_filter import StockFilter
from src.volume_analyzer import analyze_volume_surge


class StockAnalyzerGUI:
    """股票分析器GUI"""
    
    def __init__(self, root: tk.Tk, config_file: str = 'config/config.ini'):
        """
        初始化GUI
        
        Args:
            root: Tkinter根窗口
            config_file: 配置文件路径
        """
        self.root = root
        self.config = Config(config_file)
        self.config_file = config_file
        
        # 读取配置
        self.window_width = self.config.getint('GUI', 'window_width', fallback=1200)
        self.window_height = self.config.getint('GUI', 'window_height', fallback=800)
        
        # 初始化组件
        self.scheduler = TaskScheduler(config_file)
        self.downloader = DataDownloader(config_file)
        self.filter = StockFilter(config_file)
        
        # 设置回调
        self.scheduler.set_progress_callback(self.on_task_progress)
        self.scheduler.set_complete_callback(self.on_task_complete)
        
        # 状态变量
        self.is_running = False
        self.current_result_file = None
        
        # 设置窗口
        self.setup_window()
        
        # 创建界面
        self.create_widgets()
        
        # 启动定时任务
        if self.config.getboolean('Scheduler', 'enabled', fallback=True):
            self.scheduler.start()
            self.update_status()
    
    def setup_window(self):
        """设置窗口"""
        self.root.title("股票分析软件 - TradeAnalytics")
        
        # 设置窗口大小和位置（居中）
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        
        # 设置最小窗口大小
        self.root.minsize(800, 600)
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置权重使其可以调整大小
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 1. 顶部控制区
        self.create_control_panel(main_frame)
        
        # 2. 数据概览区
        self.create_overview_panel(main_frame)
        
        # 3. 结果显示区（Notebook标签页）
        self.create_result_panel(main_frame)
        
        # 4. 底部状态栏
        self.create_status_bar(main_frame)
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="控制面板", padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 按钮
        ttk.Button(control_frame, text="立即执行分析", 
                  command=self.run_analysis, width=15).grid(row=0, column=0, padx=5)
        ttk.Button(control_frame, text="成交量暴涨分析", 
                  command=self.run_volume_analysis, width=15).grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="查看历史结果", 
                  command=self.view_history, width=15).grid(row=0, column=2, padx=5)
        ttk.Button(control_frame, text="导出结果", 
                  command=self.export_results, width=15).grid(row=0, column=3, padx=5)
        ttk.Button(control_frame, text="设置", 
                  command=self.open_settings, width=15).grid(row=0, column=4, padx=5)
        
        # 状态指示器
        self.status_label = ttk.Label(control_frame, text="状态: 空闲", 
                                      foreground="green")
        self.status_label.grid(row=0, column=5, padx=20)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, length=300, 
                                           variable=self.progress_var, 
                                           mode='determinate',
                                           maximum=100)
        self.progress_bar.grid(row=0, column=6, padx=10)
        
        # 进度文本
        self.progress_label = ttk.Label(control_frame, text="")
        self.progress_label.grid(row=0, column=7, padx=5)
    
    def create_overview_panel(self, parent):
        """创建数据概览面板"""
        overview_frame = ttk.LabelFrame(parent, text="数据概览", padding="10")
        overview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 本地股票数量
        ttk.Label(overview_frame, text="本地股票数量:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.stock_count_label = ttk.Label(overview_frame, text="0", foreground="blue")
        self.stock_count_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # 最新数据日期
        ttk.Label(overview_frame, text="最新数据日期:").grid(row=0, column=2, sticky=tk.W, padx=20)
        self.latest_date_label = ttk.Label(overview_frame, text="未知", foreground="blue")
        self.latest_date_label.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # 符合条件的股票数量
        ttk.Label(overview_frame, text="符合条件股票:").grid(row=0, column=4, sticky=tk.W, padx=20)
        self.matched_count_label = ttk.Label(overview_frame, text="0", foreground="red")
        self.matched_count_label.grid(row=0, column=5, sticky=tk.W, padx=5)
        
        # 刷新按钮
        ttk.Button(overview_frame, text="刷新", 
                  command=self.refresh_overview, width=10).grid(row=0, column=6, padx=20)
        
        # 初始刷新
        self.refresh_overview()
    
    def create_result_panel(self, parent):
        """创建结果显示面板"""
        result_frame = ttk.LabelFrame(parent, text="分析结果", padding="10")
        result_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 创建Notebook
        notebook = ttk.Notebook(result_frame)
        notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标签页1：结果表格
        table_frame = ttk.Frame(notebook)
        notebook.add(table_frame, text="筛选结果")
        self.create_result_table(table_frame)
        
        # 标签页2：日志
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="运行日志")
        self.create_log_panel(log_frame)
    
    def create_result_table(self, parent):
        """创建结果表格"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 提示标签
        tip_frame = ttk.Frame(parent)
        tip_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        ttk.Label(tip_frame, text="提示: 双击股票可查看详细数据", 
                 foreground="blue", font=('', 9)).pack(side=tk.LEFT)
        
        # 创建Treeview
        columns = ('股票代码', '股票名称', '日期', '收盘价', '120日均线', 
                  '成交量', '前7日平均量', '成交量倍数')
        
        self.result_tree = ttk.Treeview(parent, columns=columns, show='headings', height=15)
        
        # 设置列标题
        for col in columns:
            self.result_tree.heading(col, text=col, 
                                    command=lambda c=col: self.sort_treeview(c))
            if col in ['股票代码', '股票名称']:
                self.result_tree.column(col, width=100, anchor=tk.CENTER)
            elif col in ['日期']:
                self.result_tree.column(col, width=100, anchor=tk.CENTER)
            else:
                self.result_tree.column(col, width=120, anchor=tk.E)
        
        # 添加滚动条
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.result_tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 绑定双击事件
        self.result_tree.bind('<Double-Button-1>', self.on_stock_double_click)
        
        # 布局
        self.result_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=1, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        # 调整行权重
        parent.rowconfigure(1, weight=1)
    
    def create_log_panel(self, parent):
        """创建日志面板"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 创建滚动文本框
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=15)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 按钮框架
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(btn_frame, text="清空日志", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="保存日志", 
                  command=self.save_log).pack(side=tk.LEFT, padx=5)
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent, relief=tk.SUNKEN, borderwidth=1)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        self.status_text = tk.StringVar()
        self.status_text.set("就绪")
        
        ttk.Label(status_frame, textvariable=self.status_text).pack(side=tk.LEFT, padx=5)
        
        # 下次执行时间
        self.next_run_label = ttk.Label(status_frame, text="")
        self.next_run_label.pack(side=tk.RIGHT, padx=5)
    
    def run_analysis(self):
        """执行分析"""
        if self.is_running:
            messagebox.showwarning("提示", "任务正在运行中，请稍候...")
            return
        
        # 确认对话框
        if not messagebox.askyesno("确认", "确定要立即执行分析吗？\n这可能需要较长时间。"):
            return
        
        self.log("开始执行分析...")
        self.status_label.config(text="状态: 运行中", foreground="orange")
        self.is_running = True
        
        # 在新线程中执行
        threading.Thread(target=self.scheduler.run_once, daemon=True).start()
    
    def view_history(self):
        """查看历史结果"""
        history_files = self.filter.get_history_results(days=30)
        
        if not history_files:
            messagebox.showinfo("提示", "没有历史结果文件")
            return
        
        # 创建选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择历史结果")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请选择要查看的结果文件:").pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for file_path in history_files:
            filename = os.path.basename(file_path)
            listbox.insert(tk.END, filename)
        
        def load_selected():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                file_path = history_files[index]
                self.load_result_file(file_path)
                dialog.destroy()
        
        ttk.Button(dialog, text="加载", command=load_selected).pack(pady=10)
    
    def export_results(self):
        """导出结果"""
        if self.current_result_file is None:
            messagebox.showwarning("提示", "没有可导出的结果")
            return
        
        # 选择保存位置
        save_path = filedialog.asksaveasfilename(
            title="导出结果",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy(self.current_result_file, save_path)
                messagebox.showinfo("成功", f"结果已导出到:\n{save_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def open_settings(self):
        """打开设置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("设置")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 创建设置表单
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 定时任务设置
        ttk.Label(frame, text="定时任务设置", font=('', 12, 'bold')).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 启用定时任务
        ttk.Label(frame, text="启用定时任务:").grid(row=1, column=0, sticky=tk.W, pady=5)
        schedule_enabled_var = tk.BooleanVar(
            value=self.config.getboolean('Scheduler', 'enabled', fallback=True))
        ttk.Checkbutton(frame, variable=schedule_enabled_var).grid(row=1, column=1, sticky=tk.W)
        
        # 执行时间
        ttk.Label(frame, text="执行时间 (HH:MM):").grid(row=2, column=0, sticky=tk.W, pady=5)
        run_time_var = tk.StringVar(value=self.config.get('Scheduler', 'run_time', fallback='15:30'))
        ttk.Entry(frame, textvariable=run_time_var, width=20).grid(row=2, column=1, sticky=tk.W)
        
        # 分析参数设置
        ttk.Label(frame, text="分析参数", font=('', 12, 'bold')).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(20, 10))
        
        # MA周期
        ttk.Label(frame, text="均线周期 (天):").grid(row=4, column=0, sticky=tk.W, pady=5)
        ma_period_var = tk.IntVar(value=self.config.getint('Analysis', 'ma_period', fallback=120))
        ttk.Entry(frame, textvariable=ma_period_var, width=20).grid(row=4, column=1, sticky=tk.W)
        
        # 成交量倍数阈值
        ttk.Label(frame, text="成交量倍数阈值:").grid(row=5, column=0, sticky=tk.W, pady=5)
        volume_ratio_var = tk.DoubleVar(
            value=self.config.getfloat('Analysis', 'volume_ratio_threshold', fallback=5.0))
        ttk.Entry(frame, textvariable=volume_ratio_var, width=20).grid(row=5, column=1, sticky=tk.W)
        
        # 下载设置
        ttk.Label(frame, text="下载设置", font=('', 12, 'bold')).grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(20, 10))
        
        # 并发数
        ttk.Label(frame, text="下载并发数:").grid(row=7, column=0, sticky=tk.W, pady=5)
        max_workers_var = tk.IntVar(value=self.config.getint('Download', 'max_workers', fallback=10))
        ttk.Entry(frame, textvariable=max_workers_var, width=20).grid(row=7, column=1, sticky=tk.W)
        
        # 保存按钮
        def save_settings():
            try:
                # 更新配置对象
                self.config.config.set('Scheduler', 'enabled', str(schedule_enabled_var.get()))
                self.config.config.set('Scheduler', 'run_time', run_time_var.get())
                self.config.config.set('Analysis', 'ma_period', str(ma_period_var.get()))
                self.config.config.set('Analysis', 'volume_ratio_threshold', 
                                      str(volume_ratio_var.get()))
                self.config.config.set('Download', 'max_workers', str(max_workers_var.get()))
                
                # 保存到文件
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    self.config.config.write(f)
                
                messagebox.showinfo("成功", "设置已保存，部分设置需要重启程序后生效")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存设置失败: {e}")
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="保存", command=save_settings, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)
    
    def refresh_overview(self):
        """刷新数据概览"""
        try:
            # 统计本地股票数量
            if os.path.exists(self.downloader.daily_dir):
                stock_files = [f for f in os.listdir(self.downloader.daily_dir) 
                              if f.endswith('.csv')]
                stock_count = len(stock_files)
                self.stock_count_label.config(text=str(stock_count))
            
            # 获取最新数据日期
            latest_date = self.downloader.get_latest_data_date()
            if latest_date:
                self.latest_date_label.config(text=latest_date)
            
            # 读取最新结果文件
            history_files = self.filter.get_history_results(days=1)
            if history_files:
                df = safe_read_csv(history_files[0])
                if df is not None:
                    self.matched_count_label.config(text=str(len(df)))
                    
        except Exception as e:
            self.log(f"刷新概览失败: {e}")
    
    def load_result_file(self, file_path: str):
        """加载结果文件"""
        try:
            df = safe_read_csv(file_path)
            if df is None:
                messagebox.showerror("错误", "无法读取结果文件")
                return
            
            # 清空表格
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            # 填充数据
            for _, row in df.iterrows():
                values = (
                    row.get('股票代码', ''),
                    row.get('股票名称', ''),
                    row.get('日期', ''),
                    f"{row.get('收盘价', 0):.2f}",
                    f"{row.get('120日均线', 0):.2f}",
                    format_number(row.get('成交量', 0)),
                    format_number(row.get('前日成交量', 0)),
                    f"{row.get('成交量倍数', 0):.2f}"
                )
                self.result_tree.insert('', tk.END, values=values)
            
            self.current_result_file = file_path
            self.log(f"已加载结果文件: {os.path.basename(file_path)}, 共 {len(df)} 只股票")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载结果失败: {e}")
    
    def sort_treeview(self, col):
        """对表格进行排序"""
        try:
            items = [(self.result_tree.set(k, col), k) 
                    for k in self.result_tree.get_children('')]
            
            # 尝试数字排序
            try:
                items.sort(key=lambda t: float(t[0].replace(',', '')), reverse=True)
            except:
                items.sort(reverse=False)
            
            for index, (val, k) in enumerate(items):
                self.result_tree.move(k, '', index)
        except Exception as e:
            self.log(f"排序失败: {e}")
    
    def log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def save_log(self):
        """保存日志"""
        save_path = filedialog.asksaveasfilename(
            title="保存日志",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("成功", "日志已保存")
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {e}")
    
    def on_task_progress(self, stage: str, current: int, total: int, message: str):
        """任务进度回调"""
        self.root.after(0, self._update_progress, stage, current, total, message)
    
    def _update_progress(self, stage: str, current: int, total: int, message: str):
        """更新进度（在主线程中）"""
        if total > 0:
            # 确保 current 不超过 total，防止进度条溢出
            current = min(current, total)
            progress = (current / total) * 100
            # 确保进度值在 0-100 之间
            progress = max(0, min(100, progress))
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{current}/{total}")
        
        self.status_text.set(f"{stage}: {message}")
        self.log(f"{stage}: {message}")
    
    def on_task_complete(self, success: bool, message: str, matched_count: int):
        """任务完成回调"""
        self.root.after(0, self._task_complete, success, message, matched_count)
    
    def _task_complete(self, success: bool, message: str, matched_count: int):
        """任务完成处理（在主线程中）"""
        self.is_running = False
        self.status_label.config(text="状态: 空闲", foreground="green")
        self.progress_var.set(0)
        self.progress_label.config(text="")
        
        if success:
            self.log(f"任务完成: {message}")
            self.status_text.set("就绪")
            
            # 刷新概览
            self.refresh_overview()
            
            # 加载最新结果
            history_files = self.filter.get_history_results(days=1)
            if history_files:
                self.load_result_file(history_files[0])
            
            messagebox.showinfo("完成", message)
        else:
            self.log(f"任务失败: {message}")
            self.status_text.set("错误")
            messagebox.showerror("错误", message)
    
    def update_status(self):
        """更新状态栏"""
        next_run = self.scheduler.get_next_run_time()
        if next_run:
            self.next_run_label.config(
                text=f"下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.next_run_label.config(text="定时任务未启用")
        
        # 定时更新
        self.root.after(60000, self.update_status)
    
    def on_stock_double_click(self, event):
        """股票双击事件 - 显示量价图"""
        selection = self.result_tree.selection()
        if not selection:
            return
        
        # 获取选中的股票代码
        item = self.result_tree.item(selection[0])
        values = item['values']
        
        if not values or len(values) < 1:
            return
        
        stock_code = str(values[0]).zfill(6)  # 确保是6位字符串，前面补0
        
        # 显示量价图
        self.show_volume_price_chart(stock_code)
    
    def show_stock_detail(self, stock_code: str, stock_name: str):
        """显示股票详细数据"""
        # 读取股票数据
        file_path = os.path.join(self.downloader.daily_dir, f"{stock_code}.csv")
        
        if not os.path.exists(file_path):
            messagebox.showwarning("提示", f"未找到股票 {stock_code} 的数据文件")
            return
        
        df = safe_read_csv(file_path)
        if df is None or df.empty:
            messagebox.showwarning("提示", f"无法读取股票 {stock_code} 的数据")
            return
        
        # 创建详情窗口
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"股票详情 - {stock_code} {stock_name}")
        detail_window.geometry("1000x600")
        detail_window.transient(self.root)
        
        # 创建框架
        main_frame = ttk.Frame(detail_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部信息区
        info_frame = ttk.LabelFrame(main_frame, text="基本信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 计算统计信息
        latest = df.iloc[-1] if len(df) > 0 else None
        
        if latest is not None:
            info_text = f"""
股票代码: {stock_code}
股票名称: {stock_name}
数据天数: {len(df)}天
日期范围: {df['date'].min()} ~ {df['date'].max()}

最新数据 ({df['date'].iloc[-1]}):
  收盘价: {latest['close']:.2f}
  开盘价: {latest['open']:.2f} 
  最高价: {latest['high']:.2f}
  最低价: {latest['low']:.2f}
  成交量: {format_number(latest['volume'])}
  成交额: {format_number(latest['amount'])}

统计数据:
  最高价: {df['close'].max():.2f}
  最低价: {df['close'].min():.2f}
  均价: {df['close'].mean():.2f}
  平均成交量: {format_number(df['volume'].mean())}
            """
            
            ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack()
        
        # 数据表格区
        table_frame = ttk.LabelFrame(main_frame, text="历史数据", padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建Treeview
        columns = ('日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # 设置列
        for col in columns:
            tree.heading(col, text=col)
            if col == '日期':
                tree.column(col, width=100, anchor=tk.CENTER)
            elif col in ['成交量', '成交额']:
                tree.column(col, width=120, anchor=tk.E)
            else:
                tree.column(col, width=80, anchor=tk.E)
        
        # 添加滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        # 填充数据（显示最近100天）
        display_df = df.tail(100)
        for _, row in display_df.iterrows():
            values = (
                row['date'],
                f"{row['open']:.2f}",
                f"{row['close']:.2f}",
                f"{row['high']:.2f}",
                f"{row['low']:.2f}",
                format_number(row['volume']),
                format_number(row['amount'])
            )
            tree.insert('', tk.END, values=values)
        
        # 布局
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        def export_data():
            """导出股票数据"""
            save_path = filedialog.asksaveasfilename(
                title="导出股票数据",
                defaultextension=".csv",
                initialfile=f"{stock_code}_{stock_name}.csv",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            if save_path:
                try:
                    df.to_csv(save_path, index=False, encoding='utf-8-sig')
                    messagebox.showinfo("成功", f"数据已导出到:\n{save_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"导出失败: {e}")
        
        ttk.Button(btn_frame, text="导出数据", command=export_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查看量价图", 
                  command=lambda: self.show_volume_price_chart(stock_code)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=detail_window.destroy).pack(side=tk.LEFT, padx=5)
        
        # 提示
        tip_label = ttk.Label(btn_frame, text=f"显示最近100天数据，共{len(df)}天", foreground="gray")
        tip_label.pack(side=tk.RIGHT, padx=5)
    
    def run_volume_analysis(self):
        """执行成交量暴涨分析"""
        if self.is_running:
            messagebox.showwarning("提示", "任务正在运行中，请稍候...")
            return
        
        # 确认对话框
        if not messagebox.askyesno("确认", "执行成交量暴涨分析？\n条件：成交量≥前日5倍 且 价格>均线"):
            return
        
        self.log("开始成交量暴涨分析...")
        self.status_label.config(text="状态: 分析中", foreground="orange")
        self.is_running = True
        
        def analysis_thread():
            try:
                # 获取所有CSV文件
                csv_files = glob.glob(os.path.join(self.downloader.daily_dir, '*.csv'))
                
                if not csv_files:
                    self.log("错误: 没有找到股票数据文件")
                    messagebox.showerror("错误", "没有找到股票数据，请先下载数据")
                    return
                
                self.log(f"找到 {len(csv_files)} 个数据文件")
                
                # 执行分析
                results_df = analyze_volume_surge(csv_files, self.on_task_progress)
                
                if results_df.empty:
                    self.log("未找到符合条件的股票")
                    messagebox.showinfo("结果", "未找到符合条件的股票")
                    return
                
                self.log(f"找到 {len(results_df)} 只符合条件的股票")
                
                # 保存结果
                output_file = os.path.join(self.filter.results_dir, 
                                          f'volume_surge_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
                results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                # 显示结果
                self.root.after(0, lambda: self.load_volume_results(results_df))
                self.log(f"结果已保存: {output_file}")
                
                messagebox.showinfo("完成", f"分析完成！找到 {len(results_df)} 只股票")
                
            except Exception as e:
                self.log(f"分析失败: {e}")
                messagebox.showerror("错误", f"分析失败: {e}")
            
            finally:
                self.is_running = False
                self.root.after(0, lambda: self.status_label.config(text="状态: 空闲", foreground="green"))
                self.root.after(0, lambda: self.progress_var.set(0))
                self.root.after(0, lambda: self.progress_label.config(text=""))
        
        # 在新线程中执行
        threading.Thread(target=analysis_thread, daemon=True).start()
    
    def load_volume_results(self, df: pd.DataFrame):
        """加载成交量分析结果"""
        try:
            # 清空现有数据
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            # 插入新数据
            for _, row in df.iterrows():
                # 确保股票代码是6位字符串格式
                stock_code = str(row['stock_code']).zfill(6)
                self.result_tree.insert('', tk.END, values=(
                    stock_code,
                    row.get('stock_name', stock_code),
                    row['date'],
                    f"{row['close']:.2f}",
                    f"{row['ma']:.2f}",
                    f"{row['volume']:,.0f}",
                    f"{row.get('avg_7day_volume', 0):,.0f}",
                    f"{row['volume_ratio']:.2f}"
                ))
            
            # 更新统计
            self.matched_count_label.config(text=str(len(df)))
            self.log(f"已加载 {len(df)} 条结果")
            
        except Exception as e:
            self.log(f"加载结果失败: {e}")
            messagebox.showerror("错误", f"加载结果失败: {e}")
    
    def show_volume_price_chart(self, stock_code: str):
        """显示股票量价图"""
        try:
            # 读取股票数据
            csv_file = os.path.join(self.downloader.daily_dir, f'{stock_code}.csv')
            
            if not os.path.exists(csv_file):
                messagebox.showerror("错误", f"未找到股票 {stock_code} 的数据文件")
                return
            
            df = pd.read_csv(csv_file)
            
            if len(df) < 10:
                messagebox.showerror("错误", "数据不足，无法绘制图表")
                return
            
            # 确保日期排序
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 获取最近60天数据
            recent_df = df.tail(60)
            
            # 计算均线
            if len(df) >= 120:
                df['ma120'] = df['close'].rolling(window=120).mean()
                recent_df = df.tail(60)
            elif len(df) >= 60:
                df['ma60'] = df['close'].rolling(window=60).mean()
                recent_df = df.tail(60)
            else:
                df['ma30'] = df['close'].rolling(window=30).mean()
                recent_df = df.tail(min(60, len(df)))
            
            # 创建新窗口
            chart_window = tk.Toplevel(self.root)
            chart_window.title(f"股票 {stock_code} 量价图")
            chart_window.geometry("1000x700")
            
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建图表
            fig = Figure(figsize=(10, 7), dpi=100)
            
            # 子图1：价格和均线
            ax1 = fig.add_subplot(211)
            ax1.plot(range(len(recent_df)), recent_df['close'].values, 
                    label='收盘价', linewidth=2, color='blue')
            
            # 绘制均线
            if 'ma120' in recent_df.columns:
                ax1.plot(range(len(recent_df)), recent_df['ma120'].values, 
                        label='120日均线', linewidth=1.5, color='orange', linestyle='--')
            elif 'ma60' in recent_df.columns:
                ax1.plot(range(len(recent_df)), recent_df['ma60'].values, 
                        label='60日均线', linewidth=1.5, color='orange', linestyle='--')
            elif 'ma30' in recent_df.columns:
                ax1.plot(range(len(recent_df)), recent_df['ma30'].values, 
                        label='30日均线', linewidth=1.5, color='orange', linestyle='--')
            
            ax1.set_title(f'{stock_code} 价格走势', fontsize=14, fontweight='bold')
            ax1.set_ylabel('价格 (元)', fontsize=12)
            ax1.legend(loc='best')
            ax1.grid(True, alpha=0.3)
            
            # 设置x轴标签
            date_labels = [d.strftime('%m-%d') for d in recent_df['date']]
            step = max(1, len(date_labels) // 10)
            ax1.set_xticks(range(0, len(date_labels), step))
            ax1.set_xticklabels([date_labels[i] for i in range(0, len(date_labels), step)], 
                               rotation=45)
            
            # 子图2：成交量
            ax2 = fig.add_subplot(212)
            colors = ['red' if i < len(recent_df) and recent_df.iloc[i]['close'] >= recent_df.iloc[i]['open'] 
                     else 'green' for i in range(len(recent_df))]
            ax2.bar(range(len(recent_df)), recent_df['volume'].values, color=colors, alpha=0.6)
            ax2.set_title('成交量', fontsize=14, fontweight='bold')
            ax2.set_xlabel('日期', fontsize=12)
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.grid(True, alpha=0.3, axis='y')
            
            # 设置x轴标签
            ax2.set_xticks(range(0, len(date_labels), step))
            ax2.set_xticklabels([date_labels[i] for i in range(0, len(date_labels), step)], 
                               rotation=45)
            
            fig.tight_layout()
            
            # 嵌入到Tkinter窗口
            canvas = FigureCanvasTkAgg(fig, master=chart_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # 添加控制按钮
            btn_frame = ttk.Frame(chart_window)
            btn_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Button(btn_frame, text="保存图表", 
                      command=lambda: self.save_chart(fig, stock_code)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="关闭", 
                      command=chart_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            self.log(f"显示图表失败: {e}")
            messagebox.showerror("错误", f"显示图表失败: {e}")
    
    def save_chart(self, fig: Figure, stock_code: str):
        """保存图表"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")],
                initialfile=f"{stock_code}_chart.png"
            )
            
            if filename:
                fig.savefig(filename, dpi=150, bbox_inches='tight')
                messagebox.showinfo("成功", f"图表已保存到: {filename}")
        
        except Exception as e:
            messagebox.showerror("错误", f"保存图表失败: {e}")
    
    def run_volume_analysis(self):
        """执行成交量暴涨分析"""
        if self.is_running:
            messagebox.showwarning("提示", "任务正在运行中，请稍候...")
            return
        
        if not messagebox.askyesno("确认", "执行成交量暴涨分析？\n条件：成交量≥前日5倍 且 价格>均线"):
            return
        
        self.log("开始成交量暴涨分析...")
        self.status_label.config(text="状态: 分析中", foreground="orange")
        self.is_running = True
        
        def analysis_thread():
            try:
                csv_files = glob.glob(os.path.join(self.downloader.daily_dir, '*.csv'))
                
                if not csv_files:
                    self.log("错误: 没有找到股票数据文件")
                    self.root.after(0, lambda: messagebox.showerror("错误", "没有找到股票数据，请先下载数据"))
                    return
                
                self.log(f"找到 {len(csv_files)} 个数据文件")
                
                # 创建简单的进度回调包装
                def progress_wrapper(current, total, message):
                    self.on_task_progress("成交量分析", current, total, message)
                
                results_df = analyze_volume_surge(csv_files, progress_wrapper)
                
                if results_df.empty:
                    self.log("未找到符合条件的股票")
                    self.root.after(0, lambda: messagebox.showinfo("结果", "未找到符合条件的股票"))
                    return
                
                self.log(f"找到 {len(results_df)} 只符合条件的股票")
                
                output_file = os.path.join(self.filter.results_dir, 
                                          f'volume_surge_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
                results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                self.root.after(0, lambda: self.load_volume_results(results_df))
                self.log(f"结果已保存: {output_file}")
                
                self.root.after(0, lambda: messagebox.showinfo("完成", f"分析完成！找到 {len(results_df)} 只股票"))
                
            except Exception as e:
                self.log(f"分析失败: {e}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"分析失败: {e}"))
            
            finally:
                self.is_running = False
                self.root.after(0, lambda: self.status_label.config(text="状态: 空闲", foreground="green"))
                self.root.after(0, lambda: self.progress_var.set(0))
                self.root.after(0, lambda: self.progress_label.config(text=""))
        
        threading.Thread(target=analysis_thread, daemon=True).start()
    
    def load_volume_results(self, df: pd.DataFrame):
        """加载成交量分析结果"""
        try:
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            for _, row in df.iterrows():
                # 确保股票代码是6位字符串格式
                stock_code = str(row['stock_code']).zfill(6)
                self.result_tree.insert('', tk.END, values=(
                    stock_code,
                    row.get('stock_name', stock_code),
                    row['date'],
                    f"{row['close']:.2f}",
                    f"{row['ma']:.2f}",
                    f"{row['volume']:,.0f}",
                    f"{row.get('avg_7day_volume', 0):,.0f}",
                    f"{row['volume_ratio']:.2f}"
                ))
            
            self.matched_count_label.config(text=str(len(df)))
            self.log(f"已加载 {len(df)} 条结果")
            
        except Exception as e:
            self.log(f"加载结果失败: {e}")
    
    def show_volume_price_chart(self, stock_code: str):
        """显示股票量价图"""
        try:
            csv_file = os.path.join(self.downloader.daily_dir, f'{stock_code}.csv')
            
            if not os.path.exists(csv_file):
                messagebox.showerror("错误", f"未找到股票 {stock_code} 的数据文件")
                return
            
            df = pd.read_csv(csv_file)
            
            if len(df) < 10:
                messagebox.showerror("错误", "数据不足，无法绘制图表")
                return
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            if len(df) >= 120:
                df['ma'] = df['close'].rolling(window=120).mean()
                ma_label = '120日均线'
            elif len(df) >= 60:
                df['ma'] = df['close'].rolling(window=60).mean()
                ma_label = '60日均线'
            else:
                df['ma'] = df['close'].rolling(window=30).mean()
                ma_label = '30日均线'
            
            recent_df = df.tail(60).reset_index(drop=True)
            
            chart_window = tk.Toplevel(self.root)
            chart_window.title(f"股票 {stock_code} 量价图")
            chart_window.geometry("1000x700")
            
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig = Figure(figsize=(10, 7), dpi=100)
            
            ax1 = fig.add_subplot(211)
            ax1.plot(range(len(recent_df)), recent_df['close'].values, 
                    label='收盘价', linewidth=2, color='blue')
            ax1.plot(range(len(recent_df)), recent_df['ma'].values, 
                    label=ma_label, linewidth=1.5, color='orange', linestyle='--')
            
            ax1.set_title(f'{stock_code} 价格走势', fontsize=14, fontweight='bold')
            ax1.set_ylabel('价格 (元)', fontsize=12)
            ax1.legend(loc='best')
            ax1.grid(True, alpha=0.3)
            
            date_labels = [d.strftime('%m-%d') for d in recent_df['date']]
            step = max(1, len(date_labels) // 10)
            ax1.set_xticks(range(0, len(date_labels), step))
            ax1.set_xticklabels([date_labels[i] for i in range(0, len(date_labels), step)], rotation=45)
            
            ax2 = fig.add_subplot(212)
            colors = ['red' if i < len(recent_df) and recent_df.iloc[i]['close'] >= recent_df.iloc[i]['open'] 
                     else 'green' for i in range(len(recent_df))]
            ax2.bar(range(len(recent_df)), recent_df['volume'].values, color=colors, alpha=0.6)
            ax2.set_title('成交量', fontsize=14, fontweight='bold')
            ax2.set_xlabel('日期', fontsize=12)
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.grid(True, alpha=0.3, axis='y')
            
            ax2.set_xticks(range(0, len(date_labels), step))
            ax2.set_xticklabels([date_labels[i] for i in range(0, len(date_labels), step)], rotation=45)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=chart_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            btn_frame = ttk.Frame(chart_window)
            btn_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Button(btn_frame, text="保存图表", 
                      command=lambda: self.save_chart(fig, stock_code)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="关闭", 
                      command=chart_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            self.log(f"显示图表失败: {e}")
            messagebox.showerror("错误", f"显示图表失败: {e}")
    
    def save_chart(self, fig: Figure, stock_code: str):
        """保存图表"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")],
                initialfile=f"{stock_code}_chart.png"
            )
            
            if filename:
                fig.savefig(filename, dpi=150, bbox_inches='tight')
                messagebox.showinfo("成功", f"图表已保存到: {filename}")
        
        except Exception as e:
            messagebox.showerror("错误", f"保存图表失败: {e}")
    
    def on_closing(self):
        """窗口关闭事件"""
        if self.is_running:
            if not messagebox.askokcancel("确认", "任务正在运行中，确定要退出吗？"):
                return
        
        # 停止定时任务
        self.scheduler.stop()
        
        self.root.destroy()


def main():
    """主函数"""
    root = tk.Tk()
    app = StockAnalyzerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
