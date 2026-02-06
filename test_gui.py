"""
测试GUI功能（使用模拟数据）
"""

import sys
import os
import tkinter as tk

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.gui import StockAnalyzerGUI

def main():
    """主函数"""
    try:
        print("启动GUI测试...")
        print("提示: 在结果表格中双击股票可以查看详细数据")
        
        # 创建主窗口
        root = tk.Tk()
        
        # 创建GUI应用
        app = StockAnalyzerGUI(root)
        
        # 如果有模拟数据，自动加载
        import glob
        result_files = glob.glob('data/results/filtered_*.csv')
        if result_files:
            print(f"自动加载结果文件: {result_files[0]}")
            app.load_result_file(result_files[0])
            app.log("提示: 双击表格中的股票可以查看详细数据")
        
        print("GUI启动成功！")
        
        # 运行主循环
        root.mainloop()
        
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
