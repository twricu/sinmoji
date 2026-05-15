#!/usr/bin/env python3
"""Sinmoji profile scorer and style prompt generator."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

AXIS_ORDER = ("pride", "envy", "wrath", "sloth", "greed", "gluttony", "lust")
BAR_WIDTH = 20
DEFAULT_THRESHOLDS = {"level_1": 10, "level_2": 20, "level_3": 40, "level_4": 100}
DEFAULT_PROFILE_JSON = r"""
{
  "created_at": "__NOW__",
  "updated_at": "__NOW__",
  "aggregate": {
    "turn_count": 0,
    "dominant_axis": null,
    "dominant_level": 0
  },
  "axes": {
    "pride": {"score": 0.0, "level": 0, "last_seen": null},
    "envy": {"score": 0.0, "level": 0, "last_seen": null},
    "wrath": {"score": 0.0, "level": 0, "last_seen": null},
    "sloth": {"score": 0.0, "level": 0, "last_seen": null},
    "greed": {"score": 0.0, "level": 0, "last_seen": null},
    "gluttony": {"score": 0.0, "level": 0, "last_seen": null},
    "lust": {"score": 0.0, "level": 0, "last_seen": null}
  }
}
"""


# 获取当前 skill 项目的根目录。
def skill_root() -> Path:
    """Return the skill root directory."""
    return Path(__file__).resolve().parents[1]


# 获取用户配置文件路径。
def config_path() -> Path:
    """Return the user-facing JSON config path."""
    return skill_root() / "config" / "sinmoji.json"


# 获取用户维护的关键词文件路径。
def keywords_path() -> Path:
    """Return the user-maintained keyword file path."""
    return skill_root() / "config" / "keywords.txt"


# 获取当前用户画像状态文件路径。
def profile_path() -> Path:
    """Return the installed skill profile state path."""
    return skill_root() / "state" / "profile.json"


# 获取画像变更快照日志文件路径。
def events_path() -> Path:
    """Return the installed skill profile change log path."""
    return skill_root() / "state" / "profile_snapshots.jsonl"


# 生成当前本地时间戳。
def now_iso() -> str:
    """Return the current local timestamp."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


# 读取 JSON 对象，文件不存在或内容异常时返回默认值。
def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    """Read a JSON object, falling back to default when the file is absent or invalid."""
    data, _ = read_json_with_fallback(path, default)
    return data


# 读取 JSON 对象，同时返回是否使用了默认值。
def read_json_with_fallback(path: Path, default: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Read JSON and report whether fallback data was used."""
    if not path.exists() or path.stat().st_size == 0:
        return dict(default), True
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return dict(default), True
    if not isinstance(data, dict):
        return dict(default), True
    return data, False


# 写入格式化 JSON，并自动创建父目录。
def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write pretty JSON and create the parent directory when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# 将配置或命令行数字限制在安全范围内。
def clamp_number(value: Any, lower: float, upper: float, fallback: float) -> float:
    """Clamp a numeric config or CLI value into a safe range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return max(lower, min(upper, float(value)))


# 加载并规范化运行时配置。
def load_config() -> dict[str, Any]:
    """Load config/sinmoji.json and fill only the defaults needed at runtime."""
    config = read_json(config_path(), {})

    # Scoring controls how one-turn LLM and keyword scores become cumulative profile deltas.
    scoring = config.setdefault("scoring", {})
    scoring["llm_score_max"] = clamp_number(scoring.get("llm_score_max", 5), 1, 10, 5)
    scoring["score_multiplier"] = clamp_number(scoring.get("score_multiplier", 3), 0, 100, 3)
    scoring["keyword_weight"] = clamp_number(scoring.get("keyword_weight", 0.2), 0, 1, 0.2)
    scoring["decay_factor"] = clamp_number(scoring.get("decay_factor", 1), 0, 1, 1)
    scoring["secondary_axis_ratio"] = clamp_number(scoring.get("secondary_axis_ratio", 0.3), 0, 1, 0.3)

    # Axis weights let each dimension grow faster or slower while keeping 1 as neutral.
    raw_axis_weights = scoring.get("axis_weights") if isinstance(scoring.get("axis_weights"), dict) else {}
    scoring["axis_weights"] = {axis: clamp_number(raw_axis_weights.get(axis, 1), 0, 100, 1) for axis in AXIS_ORDER}

    # Level thresholds map unbounded cumulative scores to Lv0-Lv4.
    thresholds = scoring.get("level_thresholds") if isinstance(scoring.get("level_thresholds"), dict) else {}
    scoring["level_thresholds"] = {
        "level_1": clamp_number(thresholds.get("level_1", 10), 0, 1_000_000, 10),
        "level_2": clamp_number(thresholds.get("level_2", 20), 0, 1_000_000, 20),
        "level_3": clamp_number(thresholds.get("level_3", 40), 0, 1_000_000, 40),
        "level_4": clamp_number(thresholds.get("level_4", 100), 0, 1_000_000, 100),
    }

    # Axis config is intentionally trusted except for missing top-level keys.
    axes = config.setdefault("axes", {})
    for axis in AXIS_ORDER:
        axis_config = axes.setdefault(axis, {})
        axis_config.setdefault("zh", axis)
        axis_config.setdefault("avatar", "")
        axis_config.setdefault("levels", {})
    config["max_profile_snapshots"] = int(clamp_number(config.get("max_profile_snapshots", 500), 1, 100_000, 500))
    return config


# 将累计分数转换为 Lv0-Lv4 等级。
def score_to_level(score: float, config: dict[str, Any]) -> int:
    """Convert an unbounded cumulative score to Lv0-Lv4."""
    thresholds = config.get("scoring", {}).get("level_thresholds", DEFAULT_THRESHOLDS)
    if score > float(thresholds.get("level_4", 100)):
        return 4
    if score >= float(thresholds.get("level_3", 40)):
        return 3
    if score >= float(thresholds.get("level_2", 20)):
        return 2
    if score >= float(thresholds.get("level_1", 10)):
        return 1
    return 0


# 创建首次运行或重置时使用的空画像。
def default_profile() -> dict[str, Any]:
    """Create a blank profile from the visible JSON text block."""
    ts = now_iso()
    return json.loads(DEFAULT_PROFILE_JSON.replace("__NOW__", ts))


# 根据各维度分数计算当前主导维度。
def aggregate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Calculate dominant axis and level from current axis scores."""
    dominant_axis = None
    dominant_score = 0.0
    for axis in AXIS_ORDER:
        score = float(profile["axes"][axis]["score"])
        if score > dominant_score:
            dominant_axis = axis
            dominant_score = score
    dominant_level = int(profile["axes"][dominant_axis]["level"]) if dominant_axis else 0
    turn_count = int(profile.get("aggregate", {}).get("turn_count", 0))
    return {"turn_count": turn_count, "dominant_axis": dominant_axis, "dominant_level": dominant_level}


# 规范化画像文件，只保留当前版本需要的字段。
def normalize_profile(raw_profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Keep only current profile fields and recalculate levels from scores."""
    profile = default_profile()
    profile["created_at"] = str(raw_profile.get("created_at", profile["created_at"]))
    profile["updated_at"] = str(raw_profile.get("updated_at", profile["updated_at"]))

    # Preserve each axis score but derive level from the active config thresholds.
    raw_axes = raw_profile.get("axes") if isinstance(raw_profile.get("axes"), dict) else {}
    for axis in AXIS_ORDER:
        raw_axis = raw_axes.get(axis) if isinstance(raw_axes.get(axis), dict) else {}
        score = max(0.0, float(raw_axis.get("score", 0.0) or 0.0))
        profile["axes"][axis] = {
            "score": round(score, 2),
            "level": score_to_level(score, config),
            "last_seen": raw_axis.get("last_seen") if isinstance(raw_axis.get("last_seen"), str) else None,
        }

    # Preserve turn count but recompute dominant values from normalized axes.
    raw_aggregate = raw_profile.get("aggregate") if isinstance(raw_profile.get("aggregate"), dict) else {}
    profile["aggregate"]["turn_count"] = int(clamp_number(raw_aggregate.get("turn_count", 0), 0, 1_000_000_000, 0))
    profile["aggregate"] = aggregate_profile(profile)
    return profile


# 加载画像文件，并在缺失时创建运行时状态文件。
def load_profile(config: dict[str, Any]) -> dict[str, Any]:
    """Load state/profile.json and create state files when missing."""
    path = profile_path()
    existed = path.exists()
    raw_profile, used_default = read_json_with_fallback(path, default_profile())
    profile = normalize_profile(raw_profile, config)
    if not existed or used_default or raw_profile != profile:
        write_json(path, profile)
    events_path().parent.mkdir(parents=True, exist_ok=True)
    events_path().touch(exist_ok=True)
    return profile


# 解析关键词文件为各维度关键词列表。
def load_keywords() -> dict[str, list[str]]:
    """Parse config/keywords.txt into axis-keyword lists."""
    keywords = {axis: [] for axis in AXIS_ORDER}
    if not keywords_path().exists():
        return keywords

    # Sections use [axis], followed by one keyword or phrase per line.
    current_axis: str | None = None
    for raw_line in keywords_path().read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            axis = line[1:-1].strip()
            current_axis = axis if axis in AXIS_ORDER else None
            continue
        if current_axis and line not in keywords[current_axis]:
            keywords[current_axis].append(line)
    return keywords


# 判断单个关键词是否命中输入文本。
def match_keyword(text: str, keyword: str) -> bool:
    """Match Chinese by substring and English-like phrases by word boundary."""
    term = keyword.strip()
    if not term:
        return False
    lowered = text.lower()
    if re.search(r"[A-Za-z0-9_]", term):
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(term.lower()) + r"(?![A-Za-z0-9_])"
        return re.search(pattern, lowered) is not None
    return term.lower() in lowered


# 使用本地关键词文件计算各维度辅助分数。
def score_text_with_keywords(text: str, config: dict[str, Any]) -> dict[str, float]:
    """Return local keyword scores in the same 0-N range as LLM scores."""
    max_score = float(config.get("scoring", {}).get("llm_score_max", 5))
    scores = {axis: 0.0 for axis in AXIS_ORDER}

    # This scorer is deliberately coarse and replaceable by a future API scorer.
    for axis, axis_keywords in load_keywords().items():
        hit_count = sum(1 for keyword in axis_keywords if match_keyword(text, keyword))
        if hit_count > 0:
            scores[axis] = min(max_score, 1.0 + (hit_count - 1) * 0.75)
    return scores


# 规范化 LLM 输入的各维度分数。
def normalized_llm_scores(raw_scores: dict[str, Any], config: dict[str, Any]) -> dict[str, float]:
    """Clamp LLM-provided axis scores to the configured range."""
    max_score = float(config.get("scoring", {}).get("llm_score_max", 5))
    return {axis: clamp_number(raw_scores.get(axis, 0), 0, max_score, 0) for axis in AXIS_ORDER}


# 累加 LLM 分数和加权关键词分数，并计算画像增量。
def calculate_deltas(llm_scores: dict[str, float], keyword_scores: dict[str, float], config: dict[str, Any]) -> dict[str, float]:
    """Add full LLM scores and weighted keyword scores, then apply cumulative multipliers."""
    scoring = config.get("scoring", {})
    keyword_weight = float(scoring.get("keyword_weight", 0.2))
    multiplier = float(scoring.get("score_multiplier", 3))
    axis_weights = scoring.get("axis_weights", {})
    deltas: dict[str, float] = {}
    for axis in AXIS_ORDER:
        merged = llm_scores[axis] + keyword_scores[axis] * keyword_weight
        axis_weight = float(axis_weights.get(axis, 1))
        deltas[axis] = round(merged * multiplier * axis_weight, 2)
    return deltas


# 将本轮画像增量应用到用户画像。
def apply_deltas(profile: dict[str, Any], deltas: dict[str, float], config: dict[str, Any]) -> bool:
    """Apply deltas to the profile and return whether any user attribute changed."""
    changed = False
    ts = now_iso()
    decay = float(config.get("scoring", {}).get("decay_factor", 1))

    # Update each axis only when its score actually changes.
    for axis in AXIS_ORDER:
        state = profile["axes"][axis]
        old_score = float(state["score"])
        delta = float(deltas.get(axis, 0.0))
        new_score = old_score + delta if delta > 0 else old_score * decay
        new_score = round(max(0.0, new_score), 2)
        if new_score == old_score:
            continue
        state["score"] = new_score
        state["level"] = score_to_level(new_score, config)
        state["last_seen"] = ts if delta > 0 else state["last_seen"]
        changed = True

    # Turn count and timestamp represent profile changes, so they move only when an axis changed.
    if changed:
        profile["updated_at"] = ts
        profile["aggregate"]["turn_count"] = int(profile["aggregate"].get("turn_count", 0)) + 1
        profile["aggregate"] = aggregate_profile(profile)
    return changed


# 选择主基调和可选副基调维度。
def style_axes(profile: dict[str, Any], config: dict[str, Any]) -> tuple[str | None, str | None]:
    """Select the dominant style axis and optional secondary axis."""
    ranked = sorted(AXIS_ORDER, key=lambda axis: float(profile["axes"][axis]["score"]), reverse=True)
    primary = ranked[0] if int(profile["axes"][ranked[0]]["level"]) > 0 else None
    if not primary:
        return None, None

    # Secondary style is suppressed unless it is strong enough relative to the primary axis.
    secondary = ranked[1]
    ratio = float(config.get("scoring", {}).get("secondary_axis_ratio", 0.3))
    primary_score = float(profile["axes"][primary]["score"])
    secondary_score = float(profile["axes"][secondary]["score"])
    if int(profile["axes"][secondary]["level"]) <= 0 or secondary_score < primary_score * ratio:
        return primary, None
    return primary, secondary


# 生成单个维度的风格说明行。
def axis_style_line(axis: str, prefix: str, profile: dict[str, Any], config: dict[str, Any]) -> str:
    """Build one style line for the primary or secondary axis."""
    axis_state = profile["axes"][axis]
    level = int(axis_state["level"])
    axis_config = config.get("axes", {}).get(axis, {})
    level_config = axis_config.get("levels", {}).get(str(level), {})
    return f"{prefix}：{axis_config.get('zh', axis)}（Lv{level}，累计分 {axis_state['score']}）- {level_config.get('style', '')}"


# 根据当前画像生成风格提示词。
def style_prompt(profile: dict[str, Any], config: dict[str, Any]) -> str:
    """Build the Sinmoji style block; return empty string below Lv1."""
    primary, secondary = style_axes(profile, config)
    if not primary:
        return ""

    # The prompt contains only active style fields and no neutral fallback.
    primary_level = int(profile["axes"][primary]["level"])
    primary_config = config.get("axes", {}).get(primary, {})
    primary_level_config = primary_config.get("levels", {}).get(str(primary_level), {})
    lines = ["[SINMOJI_STYLE]", axis_style_line(primary, "主基调", profile, config)]
    if secondary:
        lines.append(axis_style_line(secondary, "副基调", profile, config))

    emojis = " ".join(primary_level_config.get("emojis", []))
    keywords = "、".join(primary_level_config.get("keywords", []))
    example = primary_level_config.get("example_opening", "")
    lines.append(f"可用emoji：{emojis}" if emojis else "可用emoji：按需少量使用")
    if keywords:
        lines.append(f"风格关键词：{keywords}")
    if example:
        lines.append(f"回答开头示例：\"{example}\"")
    lines.append("[/SINMOJI_STYLE]")
    return "\n".join(lines)


# 构造一条不包含原始输入的有效画像变更记录。
def build_change_log(llm_scores: dict[str, float], keyword_scores: dict[str, float], deltas: dict[str, float], profile: dict[str, Any]) -> dict[str, Any]:
    """Build a compact log entry for an effective profile change."""
    changed_axes = [axis for axis in AXIS_ORDER if float(deltas.get(axis, 0.0)) != 0.0]
    return {
        "ts": profile["updated_at"],
        "llm": {axis: llm_scores[axis] for axis in changed_axes if float(llm_scores.get(axis, 0.0)) != 0.0},
        "keywords": {axis: keyword_scores[axis] for axis in changed_axes if float(keyword_scores.get(axis, 0.0)) != 0.0},
        "delta": {axis: deltas[axis] for axis in changed_axes},
        "after": {axis: profile["axes"][axis]["score"] for axis in changed_axes},
        "dominant": profile["aggregate"]["dominant_axis"],
        "level": profile["aggregate"]["dominant_level"],
    }


# 将有效画像变更记录压缩为一行写入日志。
def append_profile_log(entry: dict[str, Any], config: dict[str, Any]) -> None:
    """Append one compact profile-change entry as JSONL."""
    path = events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
        file.write("\n")

    # Keep only the configured number of latest profile change entries.
    lines = path.read_text(encoding="utf-8").splitlines()
    max_events = int(config.get("max_profile_snapshots", 500))
    if len(lines) > max_events:
        path.write_text("\n".join(lines[-max_events:]) + "\n", encoding="utf-8")


# 执行一次完整评分、画像更新和提示词生成流程。
def evaluate(raw_scores: dict[str, Any], question: str, profile: dict[str, Any], config: dict[str, Any]) -> tuple[str, bool, dict[str, Any], dict[str, Any] | None]:
    """Run the one-call pipeline and return prompt, changed flag, profile, and log entry."""
    llm_scores = normalized_llm_scores(raw_scores, config)
    keyword_scores = score_text_with_keywords(question, config)
    deltas = calculate_deltas(llm_scores, keyword_scores, config)
    changed = apply_deltas(profile, deltas, config)
    log_entry = build_change_log(llm_scores, keyword_scores, deltas, profile) if changed else None
    return style_prompt(profile, config), changed, profile, log_entry


# 渲染报告中使用的分数强度条。
def score_bar(score: float) -> str:
    """Render a capped visual bar for unbounded scores."""
    filled = max(0, min(BAR_WIDTH, int(round(min(score, 100) / 100 * BAR_WIDTH))))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


# 生成当前画像的 Markdown 报告。
def report(profile: dict[str, Any], config: dict[str, Any]) -> str:
    """Render a markdown report for the current profile."""
    lines = [
        "# Sinmoji 画像",
        "",
        f"- Updated: `{profile['updated_at']}`",
        f"- Turns: `{profile['aggregate']['turn_count']}`",
        f"- Dominant: `{profile['aggregate']['dominant_axis']}` · Lv{profile['aggregate']['dominant_level']}",
        "",
        "| 维度 | 等级 | 累计分 | 强度 | 最后出现 |",
        "|---|---:|---:|---|---|",
    ]
    for axis in AXIS_ORDER:
        axis_config = config.get("axes", {}).get(axis, {})
        state = profile["axes"][axis]
        display = f"{axis_config.get('avatar', '')} {axis} / {axis_config.get('zh', axis)}".strip()
        lines.append(f"| {display} | {state['level']} | {state['score']:.2f} | `{score_bar(float(state['score']))}` | `{state['last_seen'] or '-'}` |")
    return "\n".join(lines)


# 重置画像和画像快照日志。
def reset_state() -> dict[str, Any]:
    """Reset profile and profile-change log."""
    profile = default_profile()
    write_json(profile_path(), profile)
    events_path().parent.mkdir(parents=True, exist_ok=True)
    events_path().write_text("", encoding="utf-8")
    return profile


# 解析命令行参数并执行对应命令。
def main() -> int:
    """Parse CLI arguments and execute one Sinmoji command."""
    parser = argparse.ArgumentParser(description="Sinmoji seven-axis profile updater.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("read", help="Print raw profile JSON.")
    subparsers.add_parser("report", help="Print profile report.")
    subparsers.add_parser("reset", help="Reset runtime profile state.")

    evaluate_parser = subparsers.add_parser("evaluate", help="Update profile and print this turn's style prompt.")
    for axis in AXIS_ORDER:
        evaluate_parser.add_argument(f"--{axis}", type=float, default=0.0, help=f"{axis} LLM score, normally 0-5.")
    evaluate_parser.add_argument("--question", default="", help="Original user input for local keyword scoring; never written to logs.")

    args = parser.parse_args()
    config = load_config()

    if args.command == "reset":
        print(json.dumps(reset_state(), ensure_ascii=False, indent=2))
        return 0

    profile = load_profile(config)
    if args.command == "read":
        print(json.dumps(profile, ensure_ascii=False, indent=2))
        return 0
    if args.command == "report":
        print(report(profile, config))
        return 0
    if args.command == "evaluate":
        raw_scores = {axis: getattr(args, axis) for axis in AXIS_ORDER}
        prompt, changed, profile, log_entry = evaluate(raw_scores, args.question, profile, config)
        if changed:
            write_json(profile_path(), profile)
            append_profile_log(log_entry, config)
        if prompt:
            print(prompt)
        return 0

    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
