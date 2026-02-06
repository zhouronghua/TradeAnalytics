"""
基础功能测试脚本
用于验证各模块是否正常工作
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    try:
        from src.utils import Config, setup_logger
        from src.data_downloader import DataDownloader
        from src.data_analyzer import DataAnalyzer
        from src.stock_filter import StockFilter
        from src.scheduler import TaskScheduler
        print("  所有模块导入成功")
        return True
    except Exception as e:
        print(f"  模块导入失败: {e}")
        return False


def test_dependencies():
    """测试依赖包"""
    print("\n测试依赖包...")
    try:
        import akshare
        import pandas
        import numpy
        import schedule
        print("  akshare 版本:", akshare.__version__)
        print("  pandas 版本:", pandas.__version__)
        print("  numpy 版本:", numpy.__version__)
        print("  所有依赖包正常")
        return True
    except Exception as e:
        print(f"  依赖包测试失败: {e}")
        return False


def test_config():
    """测试配置文件"""
    print("\n测试配置文件...")
    try:
        from src.utils import Config
        config = Config('config/config.ini')
        
        ma_period = config.getint('Analysis', 'ma_period')
        volume_ratio = config.getfloat('Analysis', 'volume_ratio_threshold')
        
        print(f"  MA周期: {ma_period}")
        print(f"  成交量倍数阈值: {volume_ratio}")
        print("  配置文件读取成功")
        return True
    except Exception as e:
        print(f"  配置文件测试失败: {e}")
        return False


def test_logger():
    """测试日志系统"""
    print("\n测试日志系统...")
    try:
        from src.utils import setup_logger
        logger = setup_logger('TestLogger')
        logger.info("这是一条测试日志")
        print("  日志系统正常")
        return True
    except Exception as e:
        print(f"  日志系统测试失败: {e}")
        return False


def test_data_analyzer():
    """测试数据分析器"""
    print("\n测试数据分析器...")
    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        from src.data_analyzer import DataAnalyzer
        
        # 创建测试数据
        dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') 
                for i in range(150, 0, -1)]
        test_data = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(10, 15, 150),
            'close': np.random.uniform(10, 15, 150),
            'high': np.random.uniform(12, 16, 150),
            'low': np.random.uniform(8, 12, 150),
            'volume': np.random.uniform(1000000, 5000000, 150)
        })
        
        # 让最后一天的成交量是前一天的6倍
        test_data.loc[test_data.index[-1], 'volume'] = \
            test_data.loc[test_data.index[-2], 'volume'] * 6
        test_data.loc[test_data.index[-1], 'close'] = 14.5
        
        # 分析数据
        analyzer = DataAnalyzer(ma_period=120)
        analyzed_df = analyzer.analyze_stock(test_data)
        
        if analyzed_df is not None and 'MA120' in analyzed_df.columns:
            print("  数据分析器正常")
            
            # 测试筛选条件
            is_match, info = analyzer.check_filter_conditions(
                analyzed_df, volume_ratio_threshold=5.0)
            
            if is_match:
                print(f"  测试股票符合筛选条件")
                print(f"    价格: {info['close']:.2f}")
                print(f"    MA120: {info['ma']:.2f}")
                print(f"    成交量倍数: {info['volume_ratio']:.2f}")
            else:
                print("  测试股票不符合筛选条件（正常）")
            
            return True
        else:
            print("  数据分析器测试失败")
            return False
    except Exception as e:
        print(f"  数据分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 50)
    print("股票分析软件基础功能测试")
    print("=" * 50)
    
    results = []
    
    # 运行各项测试
    results.append(("依赖包", test_dependencies()))
    results.append(("模块导入", test_imports()))
    results.append(("配置文件", test_config()))
    results.append(("日志系统", test_logger()))
    results.append(("数据分析", test_data_analyzer()))
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "通过" if result else "失败"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"{symbol} {name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("\n所有测试通过！程序可以正常使用。")
        print("\n运行 'python main.py' 启动程序")
    else:
        print("\n部分测试失败，请检查错误信息")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
