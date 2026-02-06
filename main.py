"""
股票分析软件主程序
TradeAnalytics - 主入口
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.gui import StockAnalyzerGUI
from src.utils import setup_logger, clean_old_logs


def main():
    """主函数"""
    try:
        # 设置日志
        logger = setup_logger('Main')
        logger.info("=" * 50)
        logger.info("股票分析软件启动")
        logger.info("=" * 50)
        
        # 清理旧日志
        clean_old_logs(keep_days=30)
        
        # 创建主窗口
        root = tk.Tk()
        
        # 创建GUI应用
        app = StockAnalyzerGUI(root)
        
        logger.info("GUI界面初始化完成")
        
        # 运行主循环
        root.mainloop()
        
        logger.info("程序正常退出")
        
    except Exception as e:
        error_msg = f"程序启动失败: {e}"
        print(error_msg)
        
        try:
            logger.error(error_msg, exc_info=True)
        except:
            pass
        
        # 显示错误对话框
        try:
            messagebox.showerror("错误", error_msg)
        except:
            pass
        
        sys.exit(1)


if __name__ == '__main__':
    main()
