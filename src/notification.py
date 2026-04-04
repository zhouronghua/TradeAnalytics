"""
消息推送模块
支持多种推送方式：Server酱、企业微信、PushPlus等
"""

import requests
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import sys
import os
import glob
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, Config


class NotificationService:
    """消息推送服务"""
    
    def __init__(self, config_file: str = 'config/config.ini'):
        """
        初始化推送服务
        
        Args:
            config_file: 配置文件路径
        """
        self.config = Config(config_file)
        self.logger = setup_logger('Notification')
        
        # 读取配置
        self.enabled = self.config.getboolean('Notification', 'enabled', fallback=False)
        self.push_type = self.config.get('Notification', 'push_type', fallback='serverchan')
        
        # Server酱配置
        self.serverchan_key = self.config.get('Notification', 'serverchan_key', fallback='')
        
        # 企业微信配置
        self.qywechat_webhook = self.config.get('Notification', 'qywechat_webhook', fallback='')
        
        # PushPlus配置
        self.pushplus_token = self.config.get('Notification', 'pushplus_token', fallback='')
        
        # 微信公众号配置
        self.wechat_appid = self.config.get('Notification', 'wechat_appid', fallback='')
        self.wechat_secret = self.config.get('Notification', 'wechat_secret', fallback='')
        self.wechat_template_id = self.config.get('Notification', 'wechat_template_id', fallback='')
        self.wechat_openids = self.config.get('Notification', 'wechat_openids', fallback='')
        
        # 推送配置
        self.push_history_days = self.config.getint('Notification', 'push_history_days', fallback=3)
        self.push_max_stocks = self.config.getint('Notification', 'push_max_stocks', fallback=20)
        self.results_dir = self.config.get('Paths', 'results_dir', fallback='./data/results')
        
        # AccessToken缓存
        self._access_token = None
        self._token_expires_at = 0
        
        self.logger.info(f"消息推送服务初始化完成 (启用: {self.enabled}, 类型: {self.push_type})")
    
    def send_analysis_result(self, matched_stocks: List[Dict], 
                            analysis_date: str = None,
                            include_history: bool = True) -> bool:
        """
        发送分析结果通知
        
        Args:
            matched_stocks: 符合条件的股票列表
            analysis_date: 分析日期
            include_history: 是否包含历史对比
        
        Returns:
            是否发送成功
        """
        if not self.enabled:
            self.logger.info("消息推送未启用")
            return False
        
        if not matched_stocks:
            self.logger.info("没有符合条件的股票，跳过推送")
            return False
        
        # 生成推送内容
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        
        title = f"股票分析结果 {analysis_date}"
        
        # 获取历史数据（如果需要）
        history_data = None
        if include_history:
            history_data = self._get_history_results()
        
        content = self._format_stocks_content(matched_stocks, analysis_date, history_data)
        
        # 根据类型发送
        if self.push_type == 'serverchan':
            return self._send_serverchan(title, content)
        elif self.push_type == 'qywechat':
            return self._send_qywechat(title, content)
        elif self.push_type == 'pushplus':
            return self._send_pushplus(title, content)
        elif self.push_type == 'wechat_official':
            return self._send_wechat_official(title, content, matched_stocks)
        else:
            self.logger.error(f"不支持的推送类型: {self.push_type}")
            return False
    
    def _get_history_results(self) -> Optional[List[Tuple[str, int]]]:
        """
        获取最近几天的分析结果统计
        
        Returns:
            [(日期, 股票数量), ...] 或 None
        """
        try:
            # 查找最近的结果文件
            pattern = os.path.join(self.results_dir, 'filtered_*.csv')
            files = glob.glob(pattern)
            
            if not files:
                return None
            
            # 按时间排序
            files.sort(key=os.path.getmtime, reverse=True)
            
            # 读取最近几天的结果
            history = []
            for file_path in files[:self.push_history_days]:
                try:
                    # 从文件名提取日期
                    filename = os.path.basename(file_path)
                    date_str = filename.replace('filtered_', '').replace('.csv', '')
                    
                    # 读取文件获取股票数量
                    df = pd.read_csv(file_path)
                    count = len(df)
                    
                    # 格式化日期
                    if len(date_str) == 8:  # YYYYMMDD
                        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    else:
                        formatted_date = date_str
                    
                    history.append((formatted_date, count))
                except Exception as e:
                    self.logger.debug(f"读取历史文件失败 {file_path}: {e}")
                    continue
            
            return history if history else None
            
        except Exception as e:
            self.logger.error(f"获取历史结果失败: {e}")
            return None
    
    def _format_stocks_content(self, stocks: List[Dict], date: str, 
                               history: Optional[List[Tuple[str, int]]] = None) -> str:
        """
        格式化股票列表为推送内容
        
        Args:
            stocks: 股票列表
            date: 分析日期
        
        Returns:
            格式化后的内容
        """
        # 标题摘要
        content = f"## 📊 今日摘要\n\n"
        content += f"- 分析日期: {date}\n"
        content += f"- 符合条件股票: **{len(stocks)}** 只\n"
        content += f"- 筛选条件: 成交量≥5倍 且 价格>均线\n\n"
        
        # 历史趋势对比
        if history:
            content += f"## 📈 近{len(history)}日趋势\n\n"
            for hist_date, hist_count in history:
                # 添加趋势箭头
                if hist_date == date:
                    icon = "📍"  # 今天
                elif hist_count > len(stocks):
                    icon = "📉"  # 减少
                elif hist_count < len(stocks):
                    icon = "📈"  # 增加
                else:
                    icon = "➡️"   # 持平
                
                content += f"- {icon} {hist_date}: {hist_count} 只\n"
            
            content += "\n"
            
            # 如果有连续出现的股票，标注为强势股
            if len(history) > 1:
                continuous_stocks = self._find_continuous_stocks(stocks, history)
                if continuous_stocks:
                    content += f"## ⭐ 连续出现股票（强势）\n\n"
                    for stock_code in continuous_stocks[:5]:  # 最多显示5只
                        stock_info = next((s for s in stocks if s.get('code', s.get('stock_code')) == stock_code), None)
                        if stock_info:
                            code = stock_info.get('code', stock_info.get('stock_code', 'N/A'))
                            name = stock_info.get('name', stock_info.get('stock_name', code))
                            if name == code:
                                content += f"- {code}\n"
                            else:
                                content += f"- {code} {name}\n"
                    content += "\n"
        
        # 股票列表（按成交量倍数排序）
        content += f"## 💎 今日股票列表\n\n"
        
        for i, stock in enumerate(stocks, 1):
            code = stock.get('code', stock.get('stock_code', 'N/A'))
            name = stock.get('name', stock.get('stock_name', code))
            close = stock.get('close', 0)
            ma = stock.get('ma', 0)
            volume_ratio = stock.get('volume_ratio', 0)
            
            # 确保name不等于code（如果等于，只显示code）
            if name == code:
                stock_display = f"{code}"
            else:
                stock_display = f"{code} {name}"
            
            content += f"### {i}. {stock_display}\n\n"
            content += f"- 日期: {stock.get('date', 'N/A')}\n"
            content += f"- 收盘价: {close:.2f}元\n"
            content += f"- 均线: {ma:.2f}元\n"
            content += f"- 成交量倍数: **{volume_ratio:.2f}**\n"
            
            # 计算价格相对均线的涨幅
            if ma > 0:
                price_above = ((close - ma) / ma) * 100
                content += f"- 价格高于均线: {price_above:.2f}%\n"
            
            content += "\n"
            
            # 限制推送数量，避免内容过长
            if i >= self.push_max_stocks:
                remaining = len(stocks) - i
                if remaining > 0:
                    content += f"\n*...还有 {remaining} 只股票，详见分析结果文件*\n"
                break
        
        return content
    
    def _find_continuous_stocks(self, today_stocks: List[Dict], 
                               history: List[Tuple[str, int]]) -> List[str]:
        """
        查找连续出现的股票（强势股）
        
        Args:
            today_stocks: 今天的股票列表
            history: 历史数据
        
        Returns:
            连续出现的股票代码列表
        """
        try:
            if len(history) < 2:
                return []
            
            # 获取今天的股票代码
            today_codes = set()
            for stock in today_stocks:
                code = stock.get('code', stock.get('stock_code'))
                if code:
                    today_codes.add(str(code).zfill(6))
            
            # 读取昨天的结果文件
            yesterday_date = history[1][0] if len(history) > 1 else None
            if not yesterday_date:
                return []
            
            yesterday_file = os.path.join(self.results_dir, 
                                         f"filtered_{yesterday_date.replace('-', '')}.csv")
            
            if not os.path.exists(yesterday_file):
                return []
            
            # 读取昨天的股票代码
            df = pd.read_csv(yesterday_file, dtype={'code': str, '股票代码': str})
            
            # 尝试找到代码列
            code_column = None
            if 'code' in df.columns:
                code_column = 'code'
            elif '股票代码' in df.columns:
                code_column = '股票代码'
            else:
                return []
            
            yesterday_codes = set(df[code_column].astype(str).str.zfill(6))
            
            # 找出连续出现的股票
            continuous = list(today_codes & yesterday_codes)
            
            return continuous
            
        except Exception as e:
            self.logger.debug(f"查找连续股票失败: {e}")
            return []
    
    def _get_access_token(self) -> Optional[str]:
        """
        获取微信公众号AccessToken
        
        Returns:
            AccessToken或None
        """
        try:
            # 检查缓存是否有效
            import time
            current_time = time.time()
            
            if self._access_token and current_time < self._token_expires_at:
                return self._access_token
            
            # 请求新的AccessToken
            url = f"https://api.weixin.qq.com/cgi-bin/token"
            params = {
                'grant_type': 'client_credential',
                'appid': self.wechat_appid,
                'secret': self.wechat_secret
            }
            
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            
            if 'access_token' in result:
                self._access_token = result['access_token']
                # 提前5分钟过期，避免边界问题
                self._token_expires_at = current_time + result.get('expires_in', 7200) - 300
                self.logger.info("微信公众号AccessToken获取成功")
                return self._access_token
            else:
                self.logger.error(f"获取AccessToken失败: {result.get('errmsg', '未知错误')}")
                return None
        
        except Exception as e:
            self.logger.error(f"获取AccessToken异常: {e}")
            return None
    
    def _send_wechat_official(self, title: str, content: str, 
                             stocks: List[Dict]) -> bool:
        """
        通过微信公众号发送模板消息
        
        Args:
            title: 标题
            content: 内容
            stocks: 股票列表
        
        Returns:
            是否发送成功
        """
        if not self.wechat_appid or not self.wechat_secret:
            self.logger.error("微信公众号AppID/Secret未配置")
            return False
        
        if not self.wechat_template_id:
            self.logger.error("微信公众号模板ID未配置")
            return False
        
        if not self.wechat_openids:
            self.logger.error("微信公众号OpenID未配置")
            return False
        
        try:
            # 获取AccessToken
            access_token = self._get_access_token()
            if not access_token:
                return False
            
            # 解析OpenID列表
            openid_list = [oid.strip() for oid in self.wechat_openids.split(',') if oid.strip()]
            
            if not openid_list:
                self.logger.error("OpenID列表为空")
                return False
            
            # 准备模板数据
            template_data = self._format_template_data(title, stocks)
            
            # 发送API地址
            url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
            
            # 向每个用户发送消息
            success_count = 0
            fail_count = 0
            
            for openid in openid_list:
                try:
                    data = {
                        'touser': openid,
                        'template_id': self.wechat_template_id,
                        'data': template_data
                    }
                    
                    response = requests.post(url, json=data, timeout=10)
                    result = response.json()
                    
                    if result.get('errcode') == 0:
                        success_count += 1
                        self.logger.info(f"微信公众号推送成功: {openid}")
                    else:
                        fail_count += 1
                        self.logger.error(f"微信公众号推送失败: {openid}, {result.get('errmsg')}")
                
                except Exception as e:
                    fail_count += 1
                    self.logger.error(f"推送到 {openid} 异常: {e}")
            
            self.logger.info(f"微信公众号推送完成: 成功{success_count}, 失败{fail_count}")
            return success_count > 0
        
        except Exception as e:
            self.logger.error(f"微信公众号推送异常: {e}")
            return False
    
    def _format_template_data(self, title: str, stocks: List[Dict]) -> Dict:
        """
        格式化模板消息数据
        
        Args:
            title: 标题
            stocks: 股票列表
        
        Returns:
            模板数据字典
        """
        # 获取历史数据
        history = self._get_history_results()
        
        # 今日摘要
        today_count = len(stocks)
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # 趋势文本
        trend_text = f"今日: {today_count}只"
        if history and len(history) >= 2:
            yesterday_count = history[1][1]
            if today_count > yesterday_count:
                trend_text += " ↑"
            elif today_count < yesterday_count:
                trend_text += " ↓"
            else:
                trend_text += " →"
        
        # 前3只股票
        top_stocks_text = ""
        for i, stock in enumerate(stocks[:3], 1):
            code = stock.get('code', stock.get('stock_code', 'N/A'))
            name = stock.get('name', stock.get('stock_name', code))
            volume_ratio = stock.get('volume_ratio', 0)
            
            if name != code:
                stock_display = f"{code} {name}"
            else:
                stock_display = code
            
            top_stocks_text += f"{i}. {stock_display} (×{volume_ratio:.1f})\n"
        
        if len(stocks) > 3:
            top_stocks_text += f"...共{len(stocks)}只"
        
        # 模板数据（根据你的模板字段调整）
        template_data = {
            'first': {
                'value': title,
                'color': '#173177'
            },
            'keyword1': {
                'value': date_str,
                'color': '#173177'
            },
            'keyword2': {
                'value': f'{today_count}只',
                'color': '#FF0000' if today_count > 0 else '#999999'
            },
            'keyword3': {
                'value': trend_text,
                'color': '#173177'
            },
            'keyword4': {
                'value': top_stocks_text.strip(),
                'color': '#173177'
            },
            'remark': {
                'value': '\n成交量≥5倍 且 价格>均线\n点击查看详情',
                'color': '#999999'
            }
        }
        
        return template_data
    
    def send_serverchan_fallback(self, title: str, content: str) -> bool:
        """
        邮件等主通道失败时的 Server 酱补发。
        不检查 Notification.enabled，仅要求已配置 serverchan_key。
        """
        if not self.serverchan_key:
            self.logger.warning("Server酱SendKey未配置，跳过邮件失败回退推送")
            return False
        return self._send_serverchan(title, content)

    def send_serverchan_test(self) -> bool:
        """Server酱连通性测试（不依赖 Notification.enabled）。"""
        title = "TradeAnalytics Server酱测试"
        content = (
            f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "若收到本消息，说明 Server酱（sctapi）配置正确。"
        )
        return self.send_serverchan_fallback(title, content)

    def send_monster_stock_report_serverchan(
        self, results_df: Optional[pd.DataFrame], analysis_date: Optional[str] = None
    ) -> bool:
        """
        妖股筛选结果仅通过 Server 酱推送。
        不检查 Notification.enabled；正文格式与邮件摘要一致（复用 EmailSender 生成逻辑）。
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        from src.email_sender import EmailSender

        helper = EmailSender(self.config_file)
        if results_df is None or results_df.empty:
            title = f"[妖股筛选] {analysis_date} 未发现候选股"
            body = (
                f"分析日期: {analysis_date}\n\n"
                "本次分析未发现符合条件的妖股候选。"
            )
        else:
            title = f"[妖股筛选] {analysis_date} 发现 {len(results_df)} 只候选股"
            body = helper._monster_df_to_markdown(results_df, analysis_date)
        return self.send_serverchan_fallback(title, body)

    def _send_serverchan(self, title: str, content: str) -> bool:
        """
        通过Server酱发送消息
        
        Args:
            title: 标题
            content: 内容（支持Markdown）
        
        Returns:
            是否发送成功
        """
        if not self.serverchan_key:
            self.logger.error("Server酱SendKey未配置")
            return False
        
        try:
            # Server酱API地址
            url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"
            
            # 发送请求
            data = {
                'title': title,
                'desp': content
            }
            
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            
            if result.get('code') == 0:
                self.logger.info("Server酱推送成功")
                return True
            else:
                self.logger.error(f"Server酱推送失败: {result.get('message', '未知错误')}")
                return False
        
        except Exception as e:
            self.logger.error(f"Server酱推送异常: {e}")
            return False
    
    def _send_qywechat(self, title: str, content: str) -> bool:
        """
        通过企业微信机器人发送消息
        支持推送到多个群（用逗号或分号分隔多个Webhook）
        
        Args:
            title: 标题
            content: 内容（支持Markdown）
        
        Returns:
            是否发送成功（至少一个群推送成功）
        """
        if not self.qywechat_webhook:
            self.logger.error("企业微信Webhook未配置")
            return False
        
        try:
            # 组合标题和内容
            full_content = f"# {title}\n\n{content}"
            
            # 发送请求数据
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": full_content
                }
            }
            
            # 支持多个Webhook（用逗号或分号分隔）
            webhooks = []
            for sep in [',', ';', '|']:
                if sep in self.qywechat_webhook:
                    webhooks = [w.strip() for w in self.qywechat_webhook.split(sep) if w.strip()]
                    break
            
            if not webhooks:
                webhooks = [self.qywechat_webhook.strip()]
            
            # 向每个群发送消息
            success_count = 0
            fail_count = 0
            
            for i, webhook in enumerate(webhooks, 1):
                try:
                    if not webhook.startswith('http'):
                        self.logger.warning(f"Webhook {i} 格式错误: {webhook[:50]}...")
                        fail_count += 1
                        continue
                    
                    response = requests.post(webhook, json=data, timeout=10)
                    result = response.json()
                    
                    if result.get('errcode') == 0:
                        success_count += 1
                        self.logger.info(f"企业微信推送成功（群{i}/{len(webhooks)}）")
                    else:
                        fail_count += 1
                        self.logger.error(f"企业微信推送失败（群{i}）: {result.get('errmsg', '未知错误')}")
                
                except Exception as e:
                    fail_count += 1
                    self.logger.error(f"企业微信推送异常（群{i}）: {e}")
            
            # 只要有一个成功就算成功
            if success_count > 0:
                self.logger.info(f"企业微信推送完成: 成功{success_count}个群, 失败{fail_count}个群")
                return True
            else:
                self.logger.error(f"企业微信推送全部失败: {fail_count}个群")
                return False
        
        except Exception as e:
            self.logger.error(f"企业微信推送异常: {e}")
            return False
    
    def _send_pushplus(self, title: str, content: str) -> bool:
        """
        通过PushPlus发送消息
        
        Args:
            title: 标题
            content: 内容（支持Markdown）
        
        Returns:
            是否发送成功
        """
        if not self.pushplus_token:
            self.logger.error("PushPlus Token未配置")
            return False
        
        try:
            # PushPlus API地址
            url = "http://www.pushplus.plus/send"
            
            # 发送请求
            data = {
                'token': self.pushplus_token,
                'title': title,
                'content': content,
                'template': 'markdown'
            }
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('code') == 200:
                self.logger.info("PushPlus推送成功")
                return True
            else:
                self.logger.error(f"PushPlus推送失败: {result.get('msg', '未知错误')}")
                return False
        
        except Exception as e:
            self.logger.error(f"PushPlus推送异常: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """
        发送测试消息
        
        Returns:
            是否发送成功
        """
        title = "TradeAnalytics 测试消息"
        content = f"""
## 测试成功！

这是一条测试消息，说明推送配置正确。

- 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 推送类型: {self.push_type}

系统已准备就绪，将在每日分析完成后自动推送结果。
"""
        
        if self.push_type == 'serverchan':
            return self._send_serverchan(title, content)
        elif self.push_type == 'qywechat':
            return self._send_qywechat(title, content)
        elif self.push_type == 'pushplus':
            return self._send_pushplus(title, content)
        elif self.push_type == 'wechat_official':
            # 测试消息使用简化数据
            test_stocks = [{
                'code': '000000',
                'name': '测试股票',
                'volume_ratio': 10.0
            }]
            return self._send_wechat_official(title, content, test_stocks)
        else:
            self.logger.error(f"不支持的推送类型: {self.push_type}")
            return False


if __name__ == '__main__':
    # 测试推送功能
    print("=" * 60)
    print("测试消息推送功能")
    print("=" * 60)
    
    service = NotificationService()
    
    if not service.enabled:
        print("\n消息推送未启用，请在config.ini中配置")
        print("参考：WECHAT_PUSH_SETUP.md")
        sys.exit(1)
    
    print(f"\n推送类型: {service.push_type}")
    print("正在发送测试消息...")
    
    success = service.send_test_message()
    
    if success:
        print("\n测试成功！请检查您的微信是否收到消息。")
    else:
        print("\n测试失败，请检查配置是否正确。")
