"""
网络诊断脚本
检查AkShare数据源连接状况
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_akshare_connection():
    """测试AkShare连接"""
    print("=" * 60)
    print("AkShare数据源诊断")
    print("=" * 60)
    
    print("\n1. AkShare数据来源:")
    print("   - 东方财富网 (eastmoney.com)")
    print("   - 新浪财经 (sina.com.cn)")
    print("   - 腾讯财经 (qq.com)")
    print("   - 网易财经 (163.com)")
    
    print("\n2. 测试网络连接...")
    
    # 测试基本网络
    import socket
    
    test_sites = [
        ('quote.eastmoney.com', 80, '东方财富'),
        ('hq.sinajs.cn', 80, '新浪财经'),
        ('qt.gtimg.cn', 80, '腾讯财经'),
        ('www.baidu.com', 80, '百度')
    ]
    
    for host, port, name in test_sites:
        try:
            socket.setdefaulttimeout(5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex((host, port))
            s.close()
            
            if result == 0:
                print(f"   [OK] {name} ({host}) - 可访问")
            else:
                print(f"   [FAIL] {name} ({host}) - 无法连接")
        except Exception as e:
            print(f"   [ERROR] {name} ({host}) - {e}")
    
    print("\n3. 测试AkShare API...")
    
    try:
        import akshare as ak
        
        # 测试简单API
        print("   尝试获取股票列表（设置超时）...")
        
        import requests
        session = requests.Session()
        session.trust_env = False  # 不使用系统代理
        
        # 直接测试API
        url = "http://80.push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': 1,
            'pz': 10,
            'fields': 'f12,f14',
            'fid': 'f3'
        }
        
        response = session.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            print("   [OK] 东方财富API可访问")
            data = response.json()
            if 'data' in data and data['data']:
                print(f"   [OK] 成功获取数据")
                if 'diff' in data['data']:
                    stocks = data['data']['diff'][:3]
                    print(f"   示例股票:")
                    for stock in stocks:
                        print(f"     {stock.get('f12', 'N/A')} {stock.get('f14', 'N/A')}")
        else:
            print(f"   [FAIL] API返回: {response.status_code}")
            
    except requests.exceptions.ConnectTimeout:
        print("   [ERROR] 连接超时")
        print("   可能原因: 网络速度慢或防火墙阻止")
    except requests.exceptions.ConnectionError as e:
        print(f"   [ERROR] 连接错误: {e}")
        print("   可能原因: 网络不通或服务器问题")
    except Exception as e:
        print(f"   [ERROR] {type(e).__name__}: {e}")
    
    print("\n4. 诊断结果:")
    print("   如果以上测试都失败，可能是:")
    print("   - 防火墙阻止访问")
    print("   - 公司网络限制")
    print("   - 需要配置代理")
    print("   - 数据源暂时不可用")


def suggest_solutions():
    """提供解决方案"""
    print("\n" + "=" * 60)
    print("解决方案")
    print("=" * 60)
    
    print("""
方案1: 调整超时和重试设置
----------------------------
编辑 config/config.ini:

[Download]
retry_times = 5        # 增加重试次数
retry_delay = 10       # 增加重试间隔（秒）

方案2: 使用代理
----------------------------
如果需要通过代理访问，可以设置系统代理：

Windows:
  set http_proxy=http://proxy.example.com:8080
  set https_proxy=http://proxy.example.com:8080

Linux/Mac:
  export http_proxy=http://proxy.example.com:8080
  export https_proxy=http://proxy.example.com:8080

方案3: 切换数据源（即将实现）
----------------------------
我将为您添加备用数据源支持：
- BaoStock (免费，需注册)
- Tushare (需要token)
- 本地数据导入

方案4: 错峰下载
----------------------------
- 避开高峰时段（上午10-11点，下午2-3点）
- 建议在晚上或周末下载
- 降低并发数: max_workers = 3

方案5: 分批下载
----------------------------
修改配置只下载部分股票，多次运行：
- 第一次: 下载沪市股票（6开头）
- 第二次: 下载深市股票（0、3开头）
- 第三次: 下载科创板（688开头）
""")


if __name__ == '__main__':
    test_akshare_connection()
    suggest_solutions()
    
    print("\n" + "=" * 60)
    print("下一步")
    print("=" * 60)
    print("1. 检查网络连接")
    print("2. 尝试不同时段下载")
    print("3. 等待添加备用数据源支持")
