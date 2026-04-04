"""
邮件发送模块
支持QQ邮箱SMTP发送分析结果邮件
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, Config


class EmailSender:
    """邮件发送器"""

    def __init__(self, config_file: str = 'config/config.ini'):
        self.logger = setup_logger('EmailSender')
        self.config = Config(config_file)

        section = 'Email'
        self.enabled = self.config.getboolean(section, 'enabled', fallback=False)
        self.smtp_server = self.config.get(section, 'smtp_server', fallback='smtp.qq.com')
        self.smtp_port = self.config.getint(section, 'smtp_port', fallback=465)
        self.smtp_ssl = self.config.getboolean(section, 'smtp_ssl', fallback=True)
        self.sender_email = self.config.get(section, 'sender_email', fallback='')
        self.sender_name = self.config.get(section, 'sender_name', fallback='TradeAnalytics')
        self.auth_code = self.config.get(section, 'auth_code', fallback='')
        self.receiver_emails = self.config.get(section, 'receiver_emails', fallback='')

        self.logger.info(f"邮件发送器初始化 (启用: {self.enabled}, 服务器: {self.smtp_server})")

    def send_monster_stock_report(self, results_df: pd.DataFrame,
                                  analysis_date: str = None) -> bool:
        """发送妖股筛选报告邮件"""
        if not self.enabled:
            self.logger.warning("邮件功能未启用")
            return False

        if results_df is None or results_df.empty:
            self.logger.info("无筛选结果，发送空报告通知")
            return self._send_empty_report(analysis_date)

        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')

        subject = f"[妖股筛选] {analysis_date} 发现 {len(results_df)} 只候选股"
        html_body = self._build_monster_stock_html(results_df, analysis_date)

        return self._send_email(subject, html_body)

    def _send_empty_report(self, analysis_date: str = None) -> bool:
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        subject = f"[妖股筛选] {analysis_date} 未发现候选股"
        html = f"""
        <html><body>
        <h2>妖股筛选报告 - {analysis_date}</h2>
        <p>本次分析未发现符合条件的妖股候选。</p>
        <p style="color:#999;font-size:12px;">
        发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        TradeAnalytics 自动发送
        </p>
        </body></html>
        """
        return self._send_email(subject, html)

    def _build_monster_stock_html(self, df: pd.DataFrame, date: str) -> str:
        """构建妖股报告HTML邮件"""
        rows_html = ""
        for i, (_, row) in enumerate(df.iterrows()):
            if i >= 30:
                rows_html += f"""<tr><td colspan="12" style="text-align:center;color:#999;">
                    ...还有 {len(df) - 30} 只候选股，详见附件</td></tr>"""
                break

            _g = self._get_field
            code = str(_g(row, 'stock_code', '股票代码', '')).zfill(6)
            name = _g(row, 'stock_name', '股票名称', code)
            score = int(_g(row, 'total_score', '综合评分'))
            close = _g(row, 'close', '收盘价')
            chg = _g(row, 'change_pct', '涨跌幅(%)')
            vol_ratio = _g(row, 'volume_ratio', '量比(vs7日均)')
            rsi = _g(row, 'rsi', 'RSI(14)')
            v_score = int(_g(row, 'volume_score', '量能评分'))
            l_score = int(_g(row, 'limit_score', '涨停评分'))
            p_score = int(_g(row, 'price_score', '形态评分'))
            t_score = int(_g(row, 'tech_score', '技术评分'))
            consec = int(_g(row, 'consecutive_limits', '连板天数'))

            # 生成妖股原因文字
            reasons = self._generate_reasons(row)
            reason_text = "; ".join(reasons) if reasons else "-"

            bg = '#fff8f0' if i % 2 == 0 else '#ffffff'
            score_color = '#e74c3c' if score >= 60 else '#e67e22' if score >= 45 else '#2ecc71'
            chg_color = '#e74c3c' if chg > 0 else '#27ae60' if chg < 0 else '#333'

            rows_html += f"""
            <tr style="background:{bg};">
                <td style="padding:6px 8px;text-align:center;">{i+1}</td>
                <td style="padding:6px 8px;">{code}</td>
                <td style="padding:6px 8px;">{name}</td>
                <td style="padding:6px 8px;text-align:right;">{close:.2f}</td>
                <td style="padding:6px 8px;text-align:right;color:{chg_color};">{chg:+.2f}%</td>
                <td style="padding:6px 8px;text-align:right;">{vol_ratio:.1f}x</td>
                <td style="padding:6px 8px;text-align:right;">{rsi:.0f}</td>
                <td style="padding:6px 8px;text-align:center;font-weight:bold;color:{score_color};">{score}</td>
                <td style="padding:6px 8px;text-align:center;">{v_score}/{l_score}/{p_score}/{t_score}</td>
                <td style="padding:6px 8px;text-align:center;">{consec}</td>
                <td style="padding:6px 8px;font-size:12px;color:#555;">{reason_text}</td>
            </tr>"""

        html = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family:'Microsoft YaHei','SimHei',Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">
        <div style="max-width:1100px;margin:0 auto;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
            <div style="background:linear-gradient(135deg,#e74c3c,#c0392b);padding:20px 30px;border-radius:8px 8px 0 0;">
                <h1 style="color:#fff;margin:0;font-size:22px;">妖股筛选报告</h1>
                <p style="color:#ffd;margin:5px 0 0 0;font-size:14px;">{date} | 发现 {len(df)} 只候选股</p>
            </div>

            <div style="padding:20px 30px;">
                <h3 style="color:#333;border-bottom:2px solid #e74c3c;padding-bottom:8px;">评分维度说明</h3>
                <p style="color:#666;font-size:13px;line-height:1.8;">
                    综合评分 = 量能(0-25) + 涨停(0-25) + 形态(0-20) + 技术(0-20) + 换手(0-10)，满分100<br>
                    分项栏格式: 量能分/涨停分/形态分/技术分
                </p>

                <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:13px;margin-top:10px;">
                <thead>
                    <tr style="background:#34495e;color:#fff;">
                        <th style="padding:8px 6px;">#</th>
                        <th style="padding:8px 6px;">代码</th>
                        <th style="padding:8px 6px;">名称</th>
                        <th style="padding:8px 6px;">收盘价</th>
                        <th style="padding:8px 6px;">涨跌幅</th>
                        <th style="padding:8px 6px;">量比</th>
                        <th style="padding:8px 6px;">RSI</th>
                        <th style="padding:8px 6px;">综合分</th>
                        <th style="padding:8px 6px;">分项</th>
                        <th style="padding:8px 6px;">连板</th>
                        <th style="padding:8px 6px;">成为妖股的原因</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
                </table>
                </div>

                <p style="color:#999;font-size:11px;margin-top:20px;border-top:1px solid #eee;padding-top:10px;">
                    发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
                    TradeAnalytics 自动发送 |
                    本邮件仅供参考，不构成投资建议
                </p>
            </div>
        </div>
        </body></html>
        """
        return html

    @staticmethod
    def _get_field(row, en_name: str, cn_name: str, default=0):
        """从row中获取字段值，兼容中英文列名"""
        val = row.get(en_name)
        if val is None or (isinstance(val, float) and val != val):
            val = row.get(cn_name, default)
        return val if val is not None else default

    @staticmethod
    def _generate_reasons(row) -> List[str]:
        """根据各维度评分生成妖股原因描述"""
        reasons = []
        _g = EmailSender._get_field

        vol_score = _g(row, 'volume_score', '量能评分')
        if vol_score >= 15:
            ratio = _g(row, 'volume_ratio', '量比(vs7日均)')
            reasons.append(f"成交量暴增{ratio:.1f}倍")
        elif vol_score >= 10:
            reasons.append("量能显著放大")
        elif vol_score >= 5:
            reasons.append("量能温和放大")

        limit_score = _g(row, 'limit_score', '涨停评分')
        consec = int(_g(row, 'consecutive_limits', '连板天数'))
        limit_count = int(_g(row, 'limit_up_count', '近期涨停次数'))
        if consec >= 2:
            reasons.append(f"连续{consec}天涨停")
        elif limit_count >= 3:
            reasons.append(f"近期{limit_count}次涨停")
        elif limit_count >= 1:
            reasons.append("近期出现涨停")

        price_score = _g(row, 'price_score', '形态评分')
        if price_score >= 10:
            reasons.append("突破前期高点+均线多头")
        elif price_score >= 5:
            reasons.append("短期涨幅强劲")
        elif price_score >= 3:
            reasons.append("价格形态向好")

        tech_score = _g(row, 'tech_score', '技术评分')
        rsi = _g(row, 'rsi', 'RSI(14)')
        if tech_score >= 10:
            reasons.append("MACD金叉+RSI强势")
        elif tech_score >= 6:
            if rsi >= 60:
                reasons.append(f"RSI强势({rsi:.0f})")
            else:
                reasons.append("技术指标偏多")
        elif tech_score >= 3:
            reasons.append("技术指标温和偏多")

        turnover_score = _g(row, 'turnover_score', '换手评分')
        if turnover_score >= 6:
            reasons.append("换手率异常活跃")

        return reasons

    def _send_email(self, subject: str, html_body: str) -> bool:
        """发送HTML邮件"""
        if not self.sender_email or not self.auth_code:
            self.logger.error("邮箱账号或授权码未配置")
            return False

        receivers = [e.strip() for e in self.receiver_emails.split(',') if e.strip()]
        if not receivers:
            self.logger.error("收件人未配置")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((self.sender_name, self.sender_email))
            msg['To'] = ', '.join(receivers)
            msg['Subject'] = subject

            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            if self.smtp_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                server.starttls()

            server.login(self.sender_email, self.auth_code)
            server.sendmail(self.sender_email, receivers, msg.as_string())
            server.quit()

            self.logger.info(f"邮件发送成功: {subject} -> {receivers}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP认证失败(检查授权码): {e}")
            return False
        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}")
            return False

    def send_test(self) -> bool:
        """发送测试邮件"""
        subject = "[TradeAnalytics] 测试邮件"
        html = f"""
        <html><body style="font-family:Arial,sans-serif;padding:20px;">
        <h2>TradeAnalytics 邮件测试</h2>
        <p>恭喜! 邮件配置正确，后续妖股筛选结果将自动发送到此邮箱。</p>
        <p style="color:#999;font-size:12px;">
        发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
        </body></html>
        """
        return self._send_email(subject, html)
