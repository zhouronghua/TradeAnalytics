"""
检查微信公众号模板消息配置
"""

import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import Config


def get_access_token(appid, secret):
    """获取AccessToken"""
    try:
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            'grant_type': 'client_credential',
            'appid': appid,
            'secret': secret
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if 'access_token' in result:
            return result['access_token']
        else:
            print(f"[错误] 获取AccessToken失败: {result.get('errmsg', '未知错误')}")
            return None
    
    except Exception as e:
        print(f"[错误] 请求异常: {e}")
        return None


def get_all_templates(access_token):
    """获取所有模板"""
    try:
        url = f"https://api.weixin.qq.com/cgi-bin/template/get_all_private_template"
        params = {'access_token': access_token}
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        return result.get('template_list', [])
    
    except Exception as e:
        print(f"[错误] 请求异常: {e}")
        return []


def main():
    print("=" * 60)
    print("检查微信公众号模板消息配置")
    print("=" * 60)
    
    # 读取配置
    config = Config('config/config.ini')
    appid = config.get('Notification', 'wechat_appid', fallback='')
    secret = config.get('Notification', 'wechat_secret', fallback='')
    template_id = config.get('Notification', 'wechat_template_id', fallback='')
    
    if not appid or not secret:
        print("\n[错误] 请先在 config/config.ini 中配置AppID和Secret")
        return
    
    print(f"\nAppID: {appid}")
    
    # 获取AccessToken
    print("正在获取AccessToken...")
    access_token = get_access_token(appid, secret)
    
    if not access_token:
        print("[失败] 无法获取AccessToken")
        return
    
    print("[成功] AccessToken获取成功")
    
    # 获取模板列表
    print("\n正在获取模板列表...")
    templates = get_all_templates(access_token)
    
    if not templates:
        print("\n[警告] 当前没有模板")
        print("\n请在公众号后台添加模板：")
        print("1. 登录 https://mp.weixin.qq.com/")
        print("2. 功能 → 模板消息 → 模板库")
        print("3. 选择合适的模板（推荐：数据统计通知）")
        return
    
    print(f"\n[成功] 共有 {len(templates)} 个模板")
    print("\n" + "=" * 60)
    print("模板列表：")
    print("=" * 60)
    
    # 显示所有模板
    for i, template in enumerate(templates, 1):
        tid = template.get('template_id', '')
        title = template.get('title', '')
        primary_industry = template.get('primary_industry', '')
        deputy_industry = template.get('deputy_industry', '')
        content = template.get('content', '')
        
        print(f"\n{i}. {title}")
        print(f"   模板ID: {tid}")
        print(f"   行业: {primary_industry} - {deputy_industry}")
        print(f"   内容预览:")
        
        # 格式化显示内容
        lines = content.split('\n')
        for line in lines[:5]:  # 只显示前5行
            print(f"      {line}")
        if len(lines) > 5:
            print(f"      ...")
        
        # 检查是否是配置的模板
        if tid == template_id:
            print(f"   >>> 这是当前配置的模板 <<<")
    
    # 配置建议
    print("\n" + "=" * 60)
    print("配置建议：")
    print("=" * 60)
    
    if not template_id:
        print("\n请选择一个模板，将其模板ID添加到 config/config.ini：")
        if templates:
            print(f"\n例如：")
            print(f"wechat_template_id = {templates[0].get('template_id')}")
    else:
        # 检查配置的模板是否存在
        found = any(t.get('template_id') == template_id for t in templates)
        
        if found:
            print(f"\n[成功] 配置的模板ID有效")
            print(f"模板ID: {template_id}")
        else:
            print(f"\n[警告] 配置的模板ID不在列表中")
            print(f"当前配置: {template_id}")
            print(f"\n请检查模板ID是否正确，或选择上面列表中的模板")
    
    print("\n" + "=" * 60)
    print("配置完成后，运行 test_push.py 测试推送")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户取消")
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
