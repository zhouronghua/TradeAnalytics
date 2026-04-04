"""
妖股筛选分析模块

基于多维度综合评分体系筛选近期妖股候选:
1. 量能异动 - 成交量突增、换手率飙升
2. 涨停板分析 - 涨停次数、连板天数、封板强度
3. 价格形态 - 涨幅、突破前高、底部放量
4. 技术指标 - MACD金叉、RSI强势、均线多头排列
5. 市值与流通盘 - 小市值优先
6. 综合评分排序
"""

import pandas as pd
import numpy as np
import os
import glob
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta

from src.utils import setup_logger, safe_read_csv
from src.volume_analyzer import get_stock_name


class MonsterStockAnalyzer:
    """妖股筛选分析器"""

    # A股涨跌停幅度
    LIMIT_UP_PCT = 9.8    # 涨停判定阈值(%)，略低于10%留余量
    LIMIT_UP_PCT_ST = 4.8  # ST股涨停判定阈值(%)

    def __init__(self, config=None):
        self.logger = setup_logger('MonsterStock')

        # 默认参数，可通过config覆盖
        self.lookback_days = 30         # 回看天数
        self.volume_surge_ratio = 3.0   # 量能暴增倍数(vs 前7日均量)
        self.turnover_threshold = 5.0   # 换手率异常阈值(%)
        self.min_score = 30             # 最低入选综合评分
        self.max_market_cap = 200       # 最大流通市值(亿)，0=不限
        self.consecutive_limit_days = 2 # 连板天数阈值
        self.rsi_strong_threshold = 60  # RSI强势区间下限
        self.price_rise_pct = 10.0      # 短期涨幅阈值(%)

        if config:
            self._load_config(config)

    def _load_config(self, config):
        """从Config对象加载参数"""
        section = 'MonsterStock'
        if not config.config.has_section(section):
            return
        self.lookback_days = config.getint(section, 'lookback_days', fallback=self.lookback_days)
        self.volume_surge_ratio = config.getfloat(section, 'volume_surge_ratio', fallback=self.volume_surge_ratio)
        self.turnover_threshold = config.getfloat(section, 'turnover_threshold', fallback=self.turnover_threshold)
        self.min_score = config.getint(section, 'min_score', fallback=self.min_score)
        self.max_market_cap = config.getfloat(section, 'max_market_cap', fallback=self.max_market_cap)
        self.consecutive_limit_days = config.getint(section, 'consecutive_limit_days', fallback=self.consecutive_limit_days)
        self.rsi_strong_threshold = config.getfloat(section, 'rsi_strong_threshold', fallback=self.rsi_strong_threshold)
        self.price_rise_pct = config.getfloat(section, 'price_rise_pct', fallback=self.price_rise_pct)

    # ------------------------------------------------------------------
    # 技术指标计算
    # ------------------------------------------------------------------

    @staticmethod
    def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calc_macd(series: pd.Series, fast=12, slow=26, signal=9):
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = 2 * (dif - dea)
        return dif, dea, macd_hist

    @staticmethod
    def calc_turnover_rate(df: pd.DataFrame) -> pd.Series:
        """计算换手率(%)。需要 volume 和 turn 列，或用 volume/amount 近似"""
        if 'turn' in df.columns:
            return pd.to_numeric(df['turn'], errors='coerce')
        if 'isST' in df.columns:
            pass
        return pd.Series(np.nan, index=df.index)

    @staticmethod
    def calc_ma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period, min_periods=period).mean()

    # ------------------------------------------------------------------
    # 单股分析
    # ------------------------------------------------------------------

    def analyze_single(self, file_path: str) -> Optional[Dict]:
        """分析单只股票，返回评分详情或None"""
        try:
            df = pd.read_csv(file_path, dtype={'code': str})
            if df is None or len(df) < 30:
                return None

            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            for col in ['open', 'close', 'high', 'low', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['close', 'volume'], inplace=True)
            if len(df) < 30:
                return None

            stock_code = os.path.basename(file_path).replace('.csv', '')
            stock_name = get_stock_name(stock_code)

            is_st = ('ST' in str(stock_name)) or ('*ST' in str(stock_name))
            limit_pct = self.LIMIT_UP_PCT_ST if is_st else self.LIMIT_UP_PCT

            # 计算涨跌幅
            df['change_pct'] = df['close'].pct_change() * 100

            # 计算均线
            df['ma5'] = self.calc_ma(df['close'], 5)
            df['ma10'] = self.calc_ma(df['close'], 10)
            df['ma20'] = self.calc_ma(df['close'], 20)
            df['ma60'] = self.calc_ma(df['close'], 60)

            # 计算RSI
            df['rsi'] = self.calc_rsi(df['close'], 14)

            # 计算MACD
            df['dif'], df['dea'], df['macd_hist'] = self.calc_macd(df['close'])

            # 换手率
            df['turnover'] = self.calc_turnover_rate(df)

            # 7日平均成交量
            df['avg_vol_7'] = df['volume'].rolling(window=7).mean()

            # 涨停判定
            df['is_limit_up'] = df['change_pct'] >= limit_pct

            # 取最近lookback_days天的数据分析
            recent = df.tail(self.lookback_days).copy()
            if len(recent) < 5:
                return None

            latest = recent.iloc[-1]
            prev = recent.iloc[-2] if len(recent) >= 2 else latest

            # -------- 评分维度 --------
            score = 0
            details = {}

            # 维度1: 量能异动 (0-25分)
            vol_score = self._score_volume(recent, latest)
            score += vol_score
            details['volume_score'] = vol_score

            # 维度2: 涨停板分析 (0-25分)
            limit_score, limit_info = self._score_limit_up(recent)
            score += limit_score
            details['limit_score'] = limit_score
            details.update(limit_info)

            # 维度3: 价格形态 (0-20分)
            price_score = self._score_price_pattern(df, recent, latest)
            score += price_score
            details['price_score'] = price_score

            # 维度4: 技术指标 (0-20分)
            tech_score = self._score_technical(latest, prev)
            score += tech_score
            details['tech_score'] = tech_score

            # 维度5: 换手率 (0-10分)
            turnover_score = self._score_turnover(recent, latest)
            score += turnover_score
            details['turnover_score'] = turnover_score

            if score < self.min_score:
                return None

            # 构造结果
            result = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'date': latest['date'].strftime('%Y-%m-%d'),
                'close': float(latest['close']),
                'change_pct': float(latest['change_pct']) if pd.notna(latest['change_pct']) else 0,
                'volume': float(latest['volume']),
                'volume_ratio': float(latest['volume'] / latest['avg_vol_7']) if pd.notna(latest['avg_vol_7']) and latest['avg_vol_7'] > 0 else 0,
                'rsi': float(latest['rsi']) if pd.notna(latest['rsi']) else 0,
                'macd_hist': float(latest['macd_hist']) if pd.notna(latest['macd_hist']) else 0,
                'total_score': score,
                'is_st': is_st,
            }
            result.update(details)

            return result

        except Exception as e:
            return None

    # ------------------------------------------------------------------
    # 各维度评分
    # ------------------------------------------------------------------

    def _score_volume(self, recent: pd.DataFrame, latest: pd.Series) -> int:
        """量能异动评分 (0-25)"""
        score = 0
        avg_vol_7 = latest.get('avg_vol_7', np.nan)
        if pd.isna(avg_vol_7) or avg_vol_7 <= 0:
            return 0

        vol_ratio = latest['volume'] / avg_vol_7

        # 当日放量
        if vol_ratio >= 5.0:
            score += 15
        elif vol_ratio >= 3.0:
            score += 10
        elif vol_ratio >= 2.0:
            score += 5

        # 近3日持续放量(均量高于前期)
        if len(recent) >= 10:
            recent_3d_avg = recent.tail(3)['volume'].mean()
            prior_7d_avg = recent.iloc[-10:-3]['volume'].mean() if len(recent) >= 10 else recent['volume'].mean()
            if prior_7d_avg > 0 and recent_3d_avg / prior_7d_avg >= 2.0:
                score += 5

        # 量价齐升(最近3日价涨量增)
        if len(recent) >= 3:
            last3 = recent.tail(3)
            price_up = all(last3['close'].diff().dropna() > 0)
            vol_up = all(last3['volume'].diff().dropna() > 0)
            if price_up and vol_up:
                score += 5

        return min(score, 25)

    def _score_limit_up(self, recent: pd.DataFrame) -> tuple:
        """涨停板评分 (0-25)"""
        score = 0
        info = {}

        limit_ups = recent['is_limit_up']
        total_limits = int(limit_ups.sum())
        info['limit_up_count'] = total_limits

        # 近期涨停次数
        if total_limits >= 5:
            score += 15
        elif total_limits >= 3:
            score += 10
        elif total_limits >= 1:
            score += 5

        # 连板天数(从最新日期往前数)
        consecutive = 0
        for val in reversed(limit_ups.values):
            if val:
                consecutive += 1
            else:
                break
        info['consecutive_limits'] = consecutive

        if consecutive >= 3:
            score += 10
        elif consecutive >= 2:
            score += 7
        elif consecutive >= 1:
            score += 3

        return min(score, 25), info

    def _score_price_pattern(self, full_df: pd.DataFrame, recent: pd.DataFrame,
                             latest: pd.Series) -> int:
        """价格形态评分 (0-20)"""
        score = 0

        # 短期涨幅
        if len(recent) >= 5:
            pct_5d = (latest['close'] / recent.iloc[-5]['close'] - 1) * 100
            if pct_5d >= 20:
                score += 8
            elif pct_5d >= 10:
                score += 5
            elif pct_5d >= 5:
                score += 3

        # 突破前20日高点
        if len(recent) >= 20:
            high_20 = recent.head(len(recent) - 1)['high'].max()
            if latest['close'] > high_20:
                score += 5

        # 突破前60日高点(更强信号)
        if len(full_df) >= 60:
            prior_60 = full_df.tail(60).head(59)
            if len(prior_60) > 0 and latest['close'] > prior_60['high'].max():
                score += 4

        # 均线多头排列 (ma5 > ma10 > ma20)
        if all(pd.notna(latest.get(ma)) for ma in ['ma5', 'ma10', 'ma20']):
            if latest['ma5'] > latest['ma10'] > latest['ma20']:
                score += 3

        return min(score, 20)

    def _score_technical(self, latest: pd.Series, prev: pd.Series) -> int:
        """技术指标评分 (0-20)"""
        score = 0

        # MACD金叉
        if all(pd.notna(x) for x in [latest.get('dif'), latest.get('dea'),
                                       prev.get('dif'), prev.get('dea')]):
            if prev['dif'] <= prev['dea'] and latest['dif'] > latest['dea']:
                score += 8  # MACD刚金叉
            elif latest['dif'] > latest['dea'] and latest['macd_hist'] > 0:
                score += 4  # MACD多头

        # RSI强势区间
        rsi = latest.get('rsi', np.nan)
        if pd.notna(rsi):
            if 60 <= rsi <= 80:
                score += 6  # 强势但未超买
            elif 50 <= rsi < 60:
                score += 3
            elif rsi > 80:
                score += 2  # 超买区间，风险加分少

        # 价格站上MA20
        if pd.notna(latest.get('ma20')) and latest['close'] > latest['ma20']:
            score += 3

        # 价格站上MA60
        if pd.notna(latest.get('ma60')) and latest['close'] > latest['ma60']:
            score += 3

        return min(score, 20)

    def _score_turnover(self, recent: pd.DataFrame, latest: pd.Series) -> int:
        """换手率评分 (0-10)"""
        score = 0
        turnover = latest.get('turnover', np.nan)

        if pd.notna(turnover):
            if turnover >= 15:
                score += 8
            elif turnover >= 10:
                score += 6
            elif turnover >= self.turnover_threshold:
                score += 4
        else:
            # 无换手率数据时，用量比间接评估
            avg_vol_7 = latest.get('avg_vol_7', np.nan)
            if pd.notna(avg_vol_7) and avg_vol_7 > 0:
                vol_ratio = latest['volume'] / avg_vol_7
                if vol_ratio >= 3.0:
                    score += 4
                elif vol_ratio >= 2.0:
                    score += 2

        # 近3日换手率均值高
        if 'turnover' in recent.columns:
            recent_turnover = recent.tail(3)['turnover']
            if recent_turnover.notna().all():
                avg_turnover = recent_turnover.mean()
                if avg_turnover >= 10:
                    score += 2

        return min(score, 10)

    # ------------------------------------------------------------------
    # 批量分析
    # ------------------------------------------------------------------

    def analyze_all(self, csv_files: List[str],
                    progress_callback: Callable = None) -> pd.DataFrame:
        """
        批量分析所有股票

        Args:
            csv_files: 数据文件列表
            progress_callback: 进度回调 (current, total, message)
        """
        results = []
        total = len(csv_files)

        for i, fp in enumerate(csv_files):
            result = self.analyze_single(fp)
            if result:
                results.append(result)

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total,
                                  f"已分析: {i+1}/{total}, 候选: {len(results)}")

        if progress_callback:
            progress_callback(total, total,
                              f"分析完成: {total}/{total}, 候选: {len(results)}")

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('total_score', ascending=False)
        return df

    def run(self, daily_dir: str, results_dir: str,
            progress_callback: Callable = None) -> tuple:
        """
        完整运行妖股筛选流程

        Returns:
            (results_df, output_file_path)
        """
        csv_files = glob.glob(os.path.join(daily_dir, '*.csv'))
        if not csv_files:
            self.logger.warning("未找到股票数据文件")
            return pd.DataFrame(), None

        self.logger.info(f"开始妖股筛选: {len(csv_files)} 只股票, "
                         f"回看{self.lookback_days}天, 最低评分{self.min_score}")

        results_df = self.analyze_all(csv_files, progress_callback)

        if results_df.empty:
            self.logger.info("未发现符合条件的妖股候选")
            return results_df, None

        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(results_dir, f'monster_stock_{timestamp}.csv')

        # 选择输出列
        out_cols = [
            'stock_code', 'stock_name', 'date', 'close', 'change_pct',
            'volume', 'volume_ratio', 'rsi',
            'total_score', 'volume_score', 'limit_score', 'price_score',
            'tech_score', 'turnover_score',
            'limit_up_count', 'consecutive_limits',
        ]
        out_cols = [c for c in out_cols if c in results_df.columns]
        export_df = results_df[out_cols].copy()

        # 中文列名映射
        rename_map = {
            'stock_code': '股票代码', 'stock_name': '股票名称',
            'date': '日期', 'close': '收盘价', 'change_pct': '涨跌幅(%)',
            'volume': '成交量', 'volume_ratio': '量比(vs7日均)',
            'rsi': 'RSI(14)',
            'total_score': '综合评分', 'volume_score': '量能评分',
            'limit_score': '涨停评分', 'price_score': '形态评分',
            'tech_score': '技术评分', 'turnover_score': '换手评分',
            'limit_up_count': '近期涨停次数', 'consecutive_limits': '连板天数',
        }
        export_df.rename(columns=rename_map, inplace=True)
        export_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        self.logger.info(f"妖股筛选完成: {len(results_df)} 只候选, 已保存 {output_file}")
        return results_df, output_file
