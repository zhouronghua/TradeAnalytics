"""
获取微信公众号关注者列表
"""

import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import Config, setup_logger


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


def get_user_list(access_token, next_openid=''):
    """获取用户列表"""
    try:
        url = f"https://api.weixin.qq.com/cgi-bin/user/get"
        params = {
            'access_token': access_token,
            'next_openid': next_openid
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if result.get('errcode') == 0 or 'data' in result:
            return result
        else:
            print(f"[错误] 获取用户列表失败: {result.get('errmsg', '未知错误')}")
            return None
    
    except Exception as e:
        print(f"[错误] 请求异常: {e}")
        return None


def get_user_info(access_token, openid):
    """获取用户信息"""
    try:
        url = f"https://api.weixin.qq.com/cgi-bin/user/info"
        params = {
            'access_token': access_token,
            'openid': openid,
            'lang': 'zh_CN'
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if 'nickname' in result:
            return result
        else:
            return None
    
    except Exception as e:
        return None


def main():
    print("=" * 60)
    print("获取微信公众号关注者列表")
    print("=" * 60)
    
    # 读取配置
    config = Config('config/config.ini')
    appid = config.get('Notification', 'wechat_appid', fallback='')
    secret = config.get('Notification', 'wechat_secret', fallback='')
    
    if not appid or not secret:
        print("\n[错误] 请先在 config/config.ini 中配置：")
        print("  wechat_appid = wx你的AppID")
        print("  wechat_secret = 你的AppSecret")
        print("\n配置说明请查看：WECHAT_OFFICIAL_SETUP.md")
        return
    
    print(f"\nAppID: {appid}")
    print("正在获取AccessToken...")
    
    # 获取AccessToken
    access_token = get_access_token(appid, secret)
    if not access_token:
        print("\n[失败] 无法获取AccessToken，请检查AppID和Secret是否正确")
        return
    
    print("[成功] AccessToken获取成功")
    print(f"Token: {access_token[:20]}...")
    
    # 获取用户列表
    print("\n正在获取关注者列表...")
    all_users = []
    next_openid = ''
    
    while True:
        result = get_user_list(access_token, next_openid)
        
        if not result:
            break
        
        data = result.get('data', {})
        openid_list = data.get('openid', [])
        
        if openid_list:
            all_users.extend(openid_list)
            print(f"  已获取 {len(all_users)} 个关注者...")
        
        next_openid = result.get('next_openid', '')
        if not next_openid:
            break
    
    total = len(all_users)
    print(f"\n[成功] 共有 {total} 个关注者")
    
    if total == 0:
        print("\n[提示] 当前没有关注者，请：")
        print("  1. 用微信扫码关注你的公众号")
        print("  2. 重新运行此脚本")
        return
    
    print("\n" + "=" * 60)
    print("关注者列表：")
    print("=" * 60)
    
    # 显示用户信息
    for i, openid in enumerate(all_users, 1):
        user_info = get_user_info(access_token, openid)
        
        if user_info:
            nickname = user_info.get('nickname', '未知')
            subscribe_time = user_info.get('subscribe_time', 0)
            
            print(f"\n{i}. {nickname}")
            print(f"   OpenID: {openid}")
            print(f"   关注时间: {subscribe_time}")
        else:
            print(f"\n{i}. OpenID: {openid}")
    
    # 生成配置建议
    print("\n" + "=" * 60)
    print("配置建议：")
    print("=" * 60)
    
    if total == 1:
        print(f"\n将以下内容添加到 config/config.ini：")
        print(f"\nwechat_openids = {all_users[0]}")
    else:
        print(f"\n如果推送给所有关注者，将以下内容添加到 config/config.ini：")
        openids_str = ','.join(all_users)
        print(f"\nwechat_openids = {openids_str}")
        
        print(f"\n如果只推送给特定用户，选择对应的OpenID：")
        print(f"wechat_openids = {all_users[0]}")
        if total > 1:
            print(f"# 或推送给多个用户（用逗号分隔）")
            print(f"wechat_openids = {all_users[0]},{all_users[1]}")
    
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
