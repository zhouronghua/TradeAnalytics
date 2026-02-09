"""
测试微信推送功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.notification import NotificationService

def test():
    print("=" * 60)
    print("测试微信推送功能")
    print("=" * 60)
    
    # 创建推送服务
    service = NotificationService()
    
    # 检查是否启用
    if not service.enabled:
        print("\n[提示] 推送功能未启用")
        print("\n推荐配置：企业微信VIP群（免费+无限+多群）")
        print("快速配置：")
        print("1. 创建企业微信群，添加群机器人")
        print("2. 复制Webhook地址")
        print("3. 编辑 config/config.ini：")
        print("   [Notification]")
        print("   enabled = true")
        print("   push_type = qywechat")
        print("   qywechat_webhook = 你的Webhook地址")
        print("\n详细说明：VIP_GROUP_QUICKSTART.md（3分钟配置）")
        return
    
    print(f"\n推送类型: {service.push_type}")
    
    # 如果是企业微信，显示群数量
    if service.push_type == 'qywechat' and service.qywechat_webhook:
        webhook_count = 1
        for sep in [',', ';', '|']:
            if sep in service.qywechat_webhook:
                webhook_count = len([w for w in service.qywechat_webhook.split(sep) if w.strip()])
                break
        if webhook_count > 1:
            print(f"配置的VIP群数量: {webhook_count} 个群")
    
    # 检查配置
    if service.push_type == 'serverchan' and not service.serverchan_key:
        print("[错误] Server酱SendKey未配置")
        print("获取地址：https://sct.ftqq.com/")
        return
    elif service.push_type == 'qywechat' and not service.qywechat_webhook:
        print("[错误] 企业微信Webhook未配置")
        return
    elif service.push_type == 'pushplus' and not service.pushplus_token:
        print("[错误] PushPlus Token未配置")
        print("获取地址：http://www.pushplus.plus/")
        return
    elif service.push_type == 'wechat_official':
        if not service.wechat_appid or not service.wechat_secret:
            print("[错误] 微信公众号AppID或Secret未配置")
            print("配置说明：WECHAT_OFFICIAL_QUICKSTART.md")
            return
        if not service.wechat_template_id:
            print("[错误] 微信公众号模板ID未配置")
            print("运行 python check_template.py 查看可用模板")
            return
        if not service.wechat_openids:
            print("[错误] 微信公众号OpenID未配置")
            print("运行 python get_followers.py 获取关注者OpenID")
            return
    
    # 发送测试消息
    print("\n正在发送测试消息...")
    success = service.send_test_message()
    
    print("\n" + "=" * 60)
    if success:
        print("测试成功！")
        print("请检查您的微信是否收到测试消息。")
        print("\n如果收到消息，说明配置正确。")
        print("程序将在每日分析完成后自动推送结果。")
    else:
        print("测试失败！")
        print("请检查：")
        print("1. SendKey/Token 是否正确")
        print("2. 网络连接是否正常")
        print("3. 查看日志文件了解详细错误")
    print("=" * 60)


if __name__ == '__main__':
    test()
