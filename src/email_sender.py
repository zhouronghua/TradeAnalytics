"""
邮件发送模块
支持QQ邮箱SMTP发送分析结果邮件
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime
from typing import List, Dict, Optional, Any
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import setup_logger, Config


class EmailSender:
    """邮件发送器"""

    def __init__(self, config_file: str = 'config/config.ini'):
        self.logger = setup_logger('EmailSender')
        self.config_file = config_file
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

        if self._send_email(subject, html_body):
            return True
        self.logger.warning("邮件发送失败，尝试通过 Server 酱推送")
        md = self._monster_df_to_markdown(results_df, analysis_date)
        return self._notify_serverchan_fallback(subject, md)

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
        if self._send_email(subject, html):
            return True
        self.logger.warning("邮件发送失败，尝试通过 Server 酱推送")
        text = (
            f"分析日期: {analysis_date}\n\n"
            "本次分析未发现符合条件的妖股候选。"
        )
        return self._notify_serverchan_fallback(subject, text)

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

    def _monster_df_to_markdown(self, df: pd.DataFrame, date: str) -> str:
        """妖股结果转为 Server 酱可用的纯文本/Markdown 摘要"""
        max_rows = self.config.getint('Notification', 'push_max_stocks', fallback=20)
        lines = [
            f"分析日期: {date}",
            f"候选数量: {len(df)}",
            "",
        ]
        _g = self._get_field
        for i, (_, row) in enumerate(df.iterrows()):
            if i >= max_rows:
                lines.append(f"... 其余 {len(df) - max_rows} 只略，详见本地结果 CSV")
                break
            code = str(_g(row, 'stock_code', '股票代码', '')).zfill(6)
            name = _g(row, 'stock_name', '股票名称', code)
            score = int(_g(row, 'total_score', '综合评分'))
            close = float(_g(row, 'close', '收盘价'))
            chg = float(_g(row, 'change_pct', '涨跌幅(%)'))
            reasons = self._generate_reasons(row)
            reason_text = "; ".join(reasons) if reasons else "-"
            lines.append(
                f"- {code} {name} 收盘{close:.2f} {chg:+.2f}% 综合分{score} | {reason_text}"
            )
        lines.append("")
        lines.append(
            f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | TradeAnalytics"
        )
        return "\n".join(lines)

    def _notify_serverchan_fallback(self, title: str, content: str) -> bool:
        try:
            from src.notification import NotificationService

            notifier = NotificationService(self.config_file)
            ok = notifier.send_serverchan_fallback(title, content)
            if ok:
                self.logger.info("已通过 Server 酱发送（邮件未成功）")
            return ok
        except Exception as e:
            self.logger.error(f"Server 酱回退发送异常: {e}")
            return False

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

    def send_volume_ma_screening_report(
        self,
        matched_stocks: List[Dict],
        analysis_date: Optional[str],
        strategy_meta: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """发送放量站上均线选股结果（与 strategy_agent / 定时筛选一致）"""
        if not self.enabled:
            self.logger.warning("邮件功能未启用")
            return False
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")
        strategy_meta = strategy_meta or {}
        ma = strategy_meta.get("ma_period", "")
        vol = strategy_meta.get("volume_ratio_threshold", "")
        tag = "已验证策略" if strategy_meta.get("from_validated") else "配置回退"
        subject = f"[选股-{tag}] {analysis_date} MA{ma} 量比>={vol} | {len(matched_stocks)} 只"
        html = self._build_volume_ma_screening_html(
            matched_stocks, analysis_date, strategy_meta
        )
        if self._send_email(subject, html):
            return True
        md = self._volume_ma_to_text(matched_stocks, analysis_date, strategy_meta)
        return self._notify_serverchan_fallback(subject, md)

    def send_volume_ma_screening_empty(
        self,
        analysis_date: Optional[str],
        strategy_meta: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """当日无符合放量+均线条件的股票时发送说明邮件"""
        if not self.enabled:
            self.logger.warning("邮件功能未启用")
            return False
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")
        strategy_meta = strategy_meta or {}
        ma = strategy_meta.get("ma_period", "")
        vol = strategy_meta.get("volume_ratio_threshold", "")
        tag = "已验证策略" if strategy_meta.get("from_validated") else "配置回退"
        subject = f"[选股-{tag}] {analysis_date} MA{ma} 量比>={vol} | 无标的"
        detail = self._strategy_meta_text_html(strategy_meta)
        html = f"""
        <html><head><meta charset="utf-8"></head>
        <body style="font-family:'Microsoft YaHei',Arial,sans-serif;padding:20px;background:#f5f5f5;">
        <div style="max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:8px;">
            <h2 style="margin-top:0;">量价选股结果</h2>
            <p>分析日期: <b>{analysis_date}</b></p>
            <p>本次扫描未发现同时满足「量比阈值」且「收盘站上均线」的股票。</p>
            {detail}
            <p style="color:#999;font-size:11px;margin-top:24px;">
            发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | TradeAnalytics
            </p>
        </div></body></html>
        """
        if self._send_email(subject, html):
            return True
        text = (
            f"分析日期: {analysis_date}\n"
            "未发现符合条件的股票。\n\n"
            + self._strategy_meta_plain(strategy_meta)
        )
        return self._notify_serverchan_fallback(subject, text)

    def _strategy_meta_plain(self, strategy_meta: Dict[str, Any]) -> str:
        lines = [
            f"参数: MA{strategy_meta.get('ma_period','')} 量比>={strategy_meta.get('volume_ratio_threshold','')}",
            f"来源: {'已验证 strategy JSON' if strategy_meta.get('from_validated') else 'config.ini 回退'}",
        ]
        if strategy_meta.get("strategy_file"):
            lines.append(f"策略文件: {strategy_meta['strategy_file']}")
        cw = strategy_meta.get("composite_win_rate_pct")
        if cw is not None:
            lines.append(f"历史回测综合胜率: {cw}%")
        return "\n".join(lines)

    def _strategy_meta_text_html(self, strategy_meta: Dict[str, Any]) -> str:
        cw = strategy_meta.get("composite_win_rate_pct")
        cw_s = f"{cw}%" if cw is not None else "—"
        src = (
            "已验证 strategy_agent 输出"
            if strategy_meta.get("from_validated")
            else "config.ini [Analysis] 回退"
        )
        fpath = strategy_meta.get("strategy_file") or "—"
        return f"""
        <div style="background:#f8f9fa;padding:12px 16px;border-radius:6px;font-size:14px;color:#333;">
        <p style="margin:4px 0;"><b>条件</b>：收盘 &gt;= MA{strategy_meta.get("ma_period","")}，
        量比 &gt;= {strategy_meta.get("volume_ratio_threshold","")}</p>
        <p style="margin:4px 0;"><b>参数来源</b>：{src}</p>
        <p style="margin:4px 0;"><b>策略文件</b>：{fpath}</p>
        <p style="margin:4px 0;"><b>历史综合胜率(5/10/20日)</b>：{cw_s}</p>
        </div>
        """

    def _build_volume_ma_screening_html(
        self,
        matched_stocks: List[Dict],
        analysis_date: str,
        strategy_meta: Dict[str, Any],
    ) -> str:
        rows = ""
        max_show = 60
        ma_n = strategy_meta.get("ma_period", "")
        for i, st in enumerate(matched_stocks):
            if i >= max_show:
                rows += (
                    f"<tr><td colspan='7' style='text-align:center;color:#888;'>"
                    f"其余 {len(matched_stocks) - max_show} 只略，见 CSV 目录 data/results</td></tr>"
                )
                break
            code = str(st.get("code", "")).zfill(6)
            name = st.get("name", code)
            dt = st.get("date", "")
            if hasattr(dt, "strftime"):
                dt = dt.strftime("%Y-%m-%d")
            close = float(st.get("close", 0) or 0)
            ma = float(st.get("ma", 0) or 0)
            vr = float(st.get("volume_ratio", 0) or 0)
            bg = "#fff" if i % 2 else "#fafafa"
            rows += f"""
            <tr style="background:{bg};">
            <td style="padding:6px 8px;">{i + 1}</td>
            <td style="padding:6px 8px;">{code}</td>
            <td style="padding:6px 8px;">{name}</td>
            <td style="padding:6px 8px;">{dt}</td>
            <td style="padding:6px 8px;text-align:right;">{close:.2f}</td>
            <td style="padding:6px 8px;text-align:right;">{ma:.2f}</td>
            <td style="padding:6px 8px;text-align:right;">{vr:.2f}</td>
            </tr>"""

        detail = self._strategy_meta_text_html(strategy_meta)
        html = f"""
        <html><head><meta charset="utf-8"></head>
        <body style="font-family:'Microsoft YaHei',Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">
        <div style="max-width:1000px;margin:0 auto;background:#fff;border-radius:8px;
        box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <div style="padding:22px 28px;border-bottom:1px solid #eee;">
            <h1 style="margin:0;font-size:20px;color:#2c3e50;">量价选股 · MA{ma_n}</h1>
            <p style="margin:8px 0 0 0;color:#666;">分析日期 {analysis_date}，
            共 {len(matched_stocks)} 只</p>
        </div>
        <div style="padding:20px 28px;">
        {detail}
        <div style="overflow-x:auto;margin-top:16px;">
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr style="background:#34495e;color:#fff;">
        <th style="padding:8px;">#</th><th style="padding:8px;">代码</th><th style="padding:8px;">名称</th>
        <th style="padding:8px;">数据日</th>
        <th style="padding:8px;">收盘</th><th style="padding:8px;">MA{ma_n}</th><th style="padding:8px;">量比</th>
        </tr></thead><tbody>{rows}</tbody></table>
        </div>
        <p style="color:#999;font-size:11px;margin-top:18px;">
        发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 仅供参考，不构成投资建议</p>
        </div></div></body></html>
        """
        return html

    def _volume_ma_to_text(
        self,
        matched_stocks: List[Dict],
        analysis_date: str,
        strategy_meta: Dict[str, Any],
    ) -> str:
        max_rows = self.config.getint("Notification", "push_max_stocks", fallback=25)
        lines = [
            self._strategy_meta_plain(strategy_meta),
            "",
            f"分析日期: {analysis_date}  数量: {len(matched_stocks)}",
            "",
        ]
        for i, st in enumerate(matched_stocks):
            if i >= max_rows:
                lines.append(f"... 其余 {len(matched_stocks) - max_rows} 只略")
                break
            code = str(st.get("code", "")).zfill(6)
            name = st.get("name", code)
            dt = st.get("date", "")
            if hasattr(dt, "strftime"):
                dt = dt.strftime("%Y-%m-%d")
            lines.append(
                f"- {code} {name} {dt} 收{float(st.get('close',0) or 0):.2f} "
                f"量比{float(st.get('volume_ratio',0) or 0):.2f}"
            )
        return "\n".join(lines)

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
        if self._send_email(subject, html):
            return True
        self.logger.warning("邮件发送失败，尝试通过 Server 酱推送")
        body = (
            "本应为 TradeAnalytics 邮件测试，邮件通道未成功，改由 Server 酱送达。\n"
            "请检查 SMTP、授权码与收件人配置。"
        )
        return self._notify_serverchan_fallback(subject + " [Server酱]", body)
