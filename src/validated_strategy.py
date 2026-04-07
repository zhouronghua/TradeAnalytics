"""
加载 strategy_agent_cli 产出的已验证选股策略 (best_strategy.json)，供定时筛选使用。
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from src.utils import setup_logger


def _project_root_from_config_file(config_file: str) -> str:
    abs_cfg = os.path.abspath(config_file)
    return os.path.dirname(os.path.dirname(abs_cfg))


def _iter_candidate_json_files(agent_root: str) -> List[str]:
    if not os.path.isdir(agent_root):
        return []
    out: List[Tuple[float, str]] = []
    for name in os.listdir(agent_root):
        sub = os.path.join(agent_root, name)
        if not os.path.isdir(sub):
            continue
        path = os.path.join(sub, "best_strategy.json")
        if os.path.isfile(path):
            out.append((os.path.getmtime(path), path))
    out.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in out]


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def load_validated_strategy_file(path: str) -> Optional[Dict[str, Any]]:
    data = _load_json(path)
    if not data:
        return None
    if not data.get("validated"):
        return None
    strat = data.get("strategy") or {}
    ma = strat.get("ma_period")
    vol = strat.get("volume_ratio_threshold")
    if ma is None or vol is None:
        return None
    return data


def find_latest_validated_strategy(agent_root: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    for path in _iter_candidate_json_files(agent_root):
        data = load_validated_strategy_file(path)
        if data:
            return data, path
    return None, None


def resolve_screening_params(
    config,
    config_file: str = "config/config.ini",
) -> Tuple[Optional[int], Optional[float], Dict[str, Any]]:
    """
    返回 (ma_period, volume_ratio_threshold, meta)。
    meta 含 from_validated, label, detail 等，供日志与邮件使用。
    """
    logger = setup_logger("ValidatedStrategy")
    root = _project_root_from_config_file(config_file)
    agent_root = os.path.join(root, "build", "strategy_agent")

    fallback = True
    try:
        fallback = config.getboolean("StrategyAgent", "fallback_to_analysis_ini", fallback=True)
    except Exception:  # noqa: BLE001
        fallback = True

    explicit = ""
    try:
        explicit = config.get("StrategyAgent", "strategy_json_path", fallback="") or ""
    except Exception:  # noqa: BLE001
        explicit = ""

    explicit = explicit.strip()
    data: Optional[Dict[str, Any]] = None
    resolved_path: Optional[str] = None

    if explicit:
        abs_path = explicit if os.path.isabs(explicit) else os.path.join(root, explicit)
        if not os.path.isfile(abs_path):
            logger.error("配置的 strategy_json_path 不存在: %s", abs_path)
        else:
            data = load_validated_strategy_file(abs_path)
            if data:
                resolved_path = abs_path
            else:
                logger.warning("strategy_json_path 未通过 validated 校验: %s", abs_path)

    if data is None:
        data, resolved_path = find_latest_validated_strategy(agent_root)

    if data is not None and resolved_path:
        strat = data["strategy"]
        ma = int(strat["ma_period"])
        vol = float(strat["volume_ratio_threshold"])
        meta = {
            "from_validated": True,
            "strategy_file": resolved_path,
            "validated": bool(data.get("validated")),
            "ma_period": ma,
            "volume_ratio_threshold": vol,
            "composite_win_rate_pct": data.get("composite_win_rate_pct"),
            "backtest_start": (data.get("start_date") or ""),
            "backtest_end": (data.get("end_date") or ""),
            "strategy_name": strat.get("name", "volume_breakout_above_ma"),
        }
        logger.info(
            "使用已验证策略: MA%s 量比>=%s (文件 %s)",
            ma,
            vol,
            resolved_path,
        )
        return ma, vol, meta

    if not fallback:
        logger.error(
            "未找到已验证策略且 fallback_to_analysis_ini=false，跳过参数加载",
        )
        return None, None, {
            "from_validated": False,
            "error": "no_validated_strategy",
            "fallback_enabled": False,
        }

    try:
        ma = config.getint("Analysis", "ma_period", fallback=20)
        vol = config.getfloat("Analysis", "volume_ratio_threshold", fallback=5.0)
    except Exception:  # noqa: BLE001
        ma, vol = 20, 5.0

    logger.warning(
        "未找到已验证策略 JSON，回退到 config.ini [Analysis]: MA%s 量比>=%s",
        ma,
        vol,
    )
    return ma, vol, {
        "from_validated": False,
        "strategy_file": None,
        "validated": False,
        "ma_period": ma,
        "volume_ratio_threshold": vol,
        "composite_win_rate_pct": None,
        "fallback_enabled": True,
    }
