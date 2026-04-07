#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
选股策略 Agent CLI：在本地日线 CSV 上网格搜索放量+均线参数，
回测 2020 年以来表现，选出胜率（5/10/20 日综合）较优的策略并落盘。

后台运行示例:
  nohup python strategy_agent_cli.py --background > /dev/null 2>&1 &
或直接:
  python strategy_agent_cli.py --background

输出目录: build/strategy_agent/<run_id>/
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime
from itertools import product
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_strategy import StrategyBacktest
from src.utils import ensure_dir, safe_read_csv, setup_logger


def resolve_daily_dir(explicit: Optional[str], cwd: str) -> str:
    if explicit:
        path = os.path.abspath(explicit)
        if not os.path.isdir(path):
            raise SystemExit(f"数据目录不存在: {path}")
        return path

    candidates = [
        os.path.join(cwd, "data", "daily"),
        os.path.join(cwd, "daily"),
        cwd,
    ]
    best: Optional[str] = None
    best_n = 0
    for d in candidates:
        if not os.path.isdir(d):
            continue
        n = len(glob.glob(os.path.join(d, "*.csv")))
        if n > best_n:
            best_n = n
            best = d
    if not best or best_n == 0:
        raise SystemExit(
            "未找到日线 CSV。请使用 --data-dir 指定目录，或将数据放在 ./data/daily 或当前目录。"
        )
    return os.path.abspath(best)


def load_raw_stock_frames(
    daily_dir: str,
    start_date: str,
    end_date: Optional[str],
    min_bars: int,
    logger,
) -> Dict[str, pd.DataFrame]:
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date) if end_date else pd.to_datetime(datetime.now())
    out: Dict[str, pd.DataFrame] = {}
    files = glob.glob(os.path.join(daily_dir, "*.csv"))
    logger.info("读取原始日线 %s 个文件 (过滤后至少 %s 条)", len(files), min_bars)
    skipped = 0
    for i, file_path in enumerate(files):
        code = os.path.basename(file_path).replace(".csv", "")
        try:
            df = safe_read_csv(file_path, dtype={"code": str})
            if df is None or len(df) < 10:
                skipped += 1
                continue
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"])
            df = df[(df["date"] >= start) & (df["date"] <= end)]
            if len(df) < min_bars:
                skipped += 1
                continue
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.sort_values("date").reset_index(drop=True)
            out[code] = df
        except Exception as exc:  # noqa: BLE001
            logger.error("加载 %s 失败: %s", code, exc)
            skipped += 1
        if (i + 1) % 2000 == 0:
            logger.info("已扫描 %s/%s, 保留 %s", i + 1, len(files), len(out))
    logger.info("原始数据: %s 只股票可用, 跳过 %s", len(out), skipped)
    return out


def maybe_limit_stocks(
    raw: Dict[str, pd.DataFrame],
    max_stocks: Optional[int],
    logger,
) -> Dict[str, pd.DataFrame]:
    if not max_stocks or max_stocks >= len(raw):
        return raw
    codes = sorted(raw.keys())[:max_stocks]
    logger.info("按 --max-stocks=%s 仅用前 %s 只股票做搜索", max_stocks, len(codes))
    return {c: raw[c] for c in codes}


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if pd.isna(obj) and isinstance(obj, (float, np.floating)):
        return None
    return obj


def composite_score(
    analysis: Dict,
    min_samples_horizon: int,
    horizons: Tuple[int, ...] = (5, 10, 20),
) -> Tuple[float, bool, Dict[str, float]]:
    """平均 5/10/20 日胜率；若任一无效样本不足则视为不可用。"""
    parts: List[float] = []
    detail: Dict[str, float] = {}
    ok = True
    for h in horizons:
        key = f"hold_{h}d"
        if key not in analysis:
            ok = False
            detail[f"p{h}d"] = 0.0
            continue
        st = analysis[key]
        n = int(st.get("sample_count", 0))
        if n < min_samples_horizon:
            ok = False
        p = float(st.get("profit_probability", 0.0))
        detail[f"p{h}d"] = p
        parts.append(p)
    if not parts:
        return 0.0, False, detail
    return sum(parts) / len(parts), ok, detail


def rank_key(
    analysis: Dict,
    score: float,
    usable: bool,
    total_trades: int,
    min_total: int,
) -> Tuple:
    """排序键：优先可用策略、综合胜率、总样本、20 日均收益。"""
    h20 = analysis.get("hold_20d", {}) if analysis else {}
    mean20 = float(h20.get("mean_return", 0.0)) if h20 else 0.0
    usable_i = 1 if usable and total_trades >= min_total else 0
    return (usable_i, score, total_trades, mean20)


def parse_float_list(s: str) -> List[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def parse_int_list(s: str) -> List[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def run_search(args: argparse.Namespace) -> None:
    cwd = os.path.abspath(os.getcwd())
    daily_dir = resolve_daily_dir(args.data_dir, cwd)
    run_id = args.run_id
    out_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "strategy_agent")
    out_dir = os.path.join(out_root, run_id)
    ensure_dir(out_dir)

    logger = setup_logger("StrategyAgent")
    logger.info("工作目录: %s", cwd)
    logger.info("日线目录: %s", daily_dir)
    logger.info("输出目录: %s", out_dir)

    ma_list = parse_int_list(args.ma_periods)
    vol_list = parse_float_list(args.volume_ratios)
    max_ma = max(ma_list)
    min_bars = max_ma + 5

    raw = load_raw_stock_frames(
        daily_dir,
        args.start,
        args.end,
        min_bars,
        logger,
    )
    if not raw:
        logger.error("没有可用的股票数据，结束")
        return
    raw = maybe_limit_stocks(raw, args.max_stocks, logger)

    rows: List[Dict] = []
    best: Optional[Dict] = None
    best_key: Tuple = (-1, 0.0, 0, 0.0)

    for ma, vol in product(ma_list, vol_list):
        engine = StrategyBacktest(
            daily_dir=daily_dir,
            start_date=args.start,
            end_date=args.end,
            ma_period=ma,
            volume_ratio_threshold=vol,
            hold_days=5,
        )
        t0 = time.time()
        trades_df = engine.run_backtest_on_raw(raw)
        elapsed = time.time() - t0
        if trades_df.empty:
            logger.info("MA%s 量比%s -> 无信号 (%.1fs)", ma, vol, elapsed)
            rows.append(
                {
                    "ma_period": ma,
                    "volume_ratio_threshold": vol,
                    "total_trades": 0,
                    "score": 0.0,
                    "usable": False,
                    "elapsed_sec": round(elapsed, 2),
                }
            )
            continue
        analysis = engine.analyze_results(trades_df, profit_threshold=args.profit_threshold)
        score, usable, det = composite_score(
            analysis, args.min_samples_horizon, (5, 10, 20)
        )
        total = int(analysis.get("total_trades", len(trades_df)))
        logger.info(
            "MA%s 量比%s -> 样本 %s 综合胜率 %.2f%% usable=%s (%.1fs)",
            ma,
            vol,
            total,
            score,
            usable,
            elapsed,
        )
        row = {
            "ma_period": ma,
            "volume_ratio_threshold": vol,
            "total_trades": total,
            "score": round(score, 4),
            "usable": usable,
            **{f"win_{k}": round(v, 2) for k, v in det.items()},
            "elapsed_sec": round(elapsed, 2),
        }
        rows.append(row)

        rk = rank_key(analysis, score, usable, total, args.min_total_trades)
        if rk > best_key:
            best_key = rk
            best = {
                "ma_period": ma,
                "volume_ratio_threshold": vol,
                "engine": engine,
                "trades_df": trades_df,
                "analysis": analysis,
                "score": score,
                "usable": usable,
            }

    grid_csv = os.path.join(out_dir, "grid_search_results.csv")
    pd.DataFrame(rows).sort_values(
        ["usable", "score", "total_trades"], ascending=[False, False, False]
    ).to_csv(grid_csv, index=False, encoding="utf-8-sig")
    logger.info("网格结果: %s", grid_csv)

    if not best or best["trades_df"].empty:
        logger.error("未找到任何有信号的组合")
        return

    engine = best["engine"]
    trades_df = best["trades_df"].copy()
    analysis = best["analysis"]

    validated = (
        best["usable"]
        and int(analysis.get("total_trades", 0)) >= args.min_total_trades
        and float(best["score"]) >= args.min_composite_win
    )

    trades_df["source_csv"] = trades_df["stock_code"].apply(
        lambda c: os.path.join(daily_dir, f"{c}.csv")
    )

    trades_csv = os.path.join(out_dir, "best_strategy_trades.csv")
    trades_df.to_csv(trades_csv, index=False, encoding="utf-8-sig")

    strategy_payload = {
        "validated": validated,
        "criteria": {
            "min_total_trades": args.min_total_trades,
            "min_samples_per_horizon": args.min_samples_horizon,
            "min_composite_win_pct": args.min_composite_win,
            "profit_threshold_pct": args.profit_threshold,
        },
        "data_dir": daily_dir,
        "start_date": args.start,
        "end_date": args.end or datetime.now().strftime("%Y-%m-%d"),
        "strategy": {
            "name": "volume_breakout_above_ma",
            "ma_period": best["ma_period"],
            "volume_ratio_threshold": best["volume_ratio_threshold"],
        },
        "composite_win_rate_pct": round(float(best["score"]), 4),
        "analysis": _json_safe(analysis),
    }

    strategy_json = os.path.join(out_dir, "best_strategy.json")
    with open(strategy_json, "w", encoding="utf-8") as f:
        json.dump(strategy_payload, f, ensure_ascii=False, indent=2)
    logger.info("策略文件: %s (validated=%s)", strategy_json, validated)

    report_txt = os.path.join(out_dir, "best_strategy_report.txt")
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("选股策略 Agent 报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"数据目录: {daily_dir}\n")
        f.write(f"区间: {args.start} ~ {strategy_payload['end_date']}\n")
        f.write(f"最优参数: MA{best['ma_period']}, 量比>={best['volume_ratio_threshold']}\n")
        f.write(f"综合胜率(5/10/20日): {best['score']:.2f}%\n")
        f.write(f"通过验证: {validated}\n\n")
        for h in (5, 10, 20):
            key = f"hold_{h}d"
            if key in analysis:
                st = analysis[key]
                f.write(
                    f"持有{h}日: 样本{st['sample_count']} "
                    f"胜率{st['profit_probability']}% "
                    f"均值{st['mean_return']}%\n"
                )
        f.write(f"\n交易明细: {trades_csv}\n")

    cols_save = [
        "stock_code",
        "stock_name",
        "date",
        "buy_price",
        "bar_open",
        "bar_high",
        "bar_low",
        "volume",
        "volume_ratio",
        "ma_value",
        "return_5d",
        "return_10d",
        "return_20d",
        "source_csv",
    ]
    existing = [c for c in cols_save if c in trades_df.columns]
    snapshot_csv = os.path.join(out_dir, "signal_bars_and_returns.csv")
    trades_df[existing].to_csv(snapshot_csv, index=False, encoding="utf-8-sig")
    logger.info("信号日 OHLC 与收益: %s", snapshot_csv)
    logger.info("完成。交易记录: %s", trades_csv)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="选股策略网格搜索 Agent (2020+ 回测)")
    p.add_argument("--data-dir", type=str, default=None, help="日线 CSV 目录 (默认自动发现)")
    p.add_argument("--start", type=str, default="2020-01-01", help="回测开始日")
    p.add_argument("--end", type=str, default=None, help="回测结束日，默认今天")
    p.add_argument(
        "--ma-periods",
        type=str,
        default="20,60,120",
        help="逗号分隔 MA 周期",
    )
    p.add_argument(
        "--volume-ratios",
        type=str,
        default="1.5,2.0,2.5,3.0,4.0,5.0",
        help="逗号分隔量比阈值",
    )
    p.add_argument("--min-total-trades", type=int, default=100, help="验证所需最少信号数")
    p.add_argument(
        "--min-samples-horizon",
        type=int,
        default=50,
        help="每个持有周期最少样本，否则该组合不计为 usable",
    )
    p.add_argument(
        "--min-composite-win",
        type=float,
        default=52.0,
        help="验证所需最低综合胜率(%%)，为 5/10/20 日胜率简单平均",
    )
    p.add_argument(
        "--profit-threshold",
        type=float,
        default=0.0,
        help="判为盈利的收益率下限(%%)",
    )
    p.add_argument("--run-id", type=str, default=None, help="输出子目录名，默认时间戳")
    p.add_argument(
        "--max-stocks",
        type=int,
        default=None,
        help="仅取按代码排序的前 N 只股票，加快试验 (默认全市场)",
    )
    p.add_argument(
        "--background",
        action="store_true",
        help="后台运行 (POSIX)，日志写入 build/strategy_agent/<run_id>/agent.log",
    )
    return p


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not args.run_id:
        args.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    out_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "build",
        "strategy_agent",
        args.run_id,
    )

    if args.background:
        ensure_dir(out_dir)
        if os.name != "posix":
            print("--background 需要 POSIX 系统", file=sys.stderr)
            sys.exit(1)
        pid = os.fork()
        if pid > 0:
            log_path = os.path.join(out_dir, "agent.log")
            print(f"已在后台启动，run_id={args.run_id}")
            print(f"日志: {log_path}")
            sys.exit(0)
        os.setsid()
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        sys.stdout.flush()
        sys.stderr.flush()
        with open(os.devnull, "r", encoding="utf-8") as dev_r:
            os.dup2(dev_r.fileno(), sys.stdin.fileno())
        log_f = open(os.path.join(out_dir, "agent.log"), "a", encoding="utf-8", buffering=1)
        os.dup2(log_f.fileno(), sys.stdout.fileno())
        os.dup2(log_f.fileno(), sys.stderr.fileno())
        with open(os.path.join(out_dir, "agent.pid"), "w", encoding="utf-8") as pf:
            pf.write(str(os.getpid()))

    run_search(args)


if __name__ == "__main__":
    main()
