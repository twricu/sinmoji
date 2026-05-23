#!/usr/bin/env python3
"""Sinmoji profile scorer and style prompt generator."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

MIN_PYTHON_VERSION = (3, 8)
AXIS_ORDER = ("pride", "envy", "wrath", "sloth", "greed", "gluttony", "lust")
BAR_WIDTH = 20
# Maximum original user-input length that is safe for preference scoring.
MAX_QUESTION_LENGTH = 200
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


def ensure_runtime() -> None:
    """Validate Python runtime and prefer UTF-8 console output."""
    if sys.version_info < MIN_PYTHON_VERSION:
        required = ".".join(str(part) for part in MIN_PYTHON_VERSION)
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raise SystemExit(f"Sinmoji requires Python {required}+; current Python is {current}.")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def skill_root() -> Path:
    """Return the skill root directory."""
    return Path(__file__).resolve().parents[1]


def config_path() -> Path:
    """Return the user-facing JSON config path."""
    return skill_root() / "config" / "sinmoji.json"


def keywords_path() -> Path:
    """Return the user-maintained keyword file path."""
    return skill_root() / "config" / "keywords.txt"


def profile_path() -> Path:
    """Return the installed skill profile state path."""
    return skill_root() / "state" / "profile.json"


def events_path() -> Path:
    """Return the installed skill profile change log path."""
    return skill_root() / "state" / "profile_snapshots.jsonl"


def now_iso() -> str:
    """Return the current local timestamp."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    """Read a required JSON object."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text with stable LF newlines on Python 3.8+."""
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write pretty JSON and create the parent directory when needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def clamp_number(value: Any, lower: float, upper: float, fallback: float) -> float:
    """Clamp a numeric config or CLI value into a safe range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return max(lower, min(upper, float(value)))


def load_config() -> dict[str, Any]:
    """Load the required config/sinmoji.json."""
    return read_json(config_path())


def score_to_level(score: float, config: dict[str, Any]) -> int:
    """Convert an unbounded cumulative score to Lv0-Lv4."""
    thresholds = config["scoring"]["level_thresholds"]
    if score > float(thresholds["level_4"]):
        return 4
    if score >= float(thresholds["level_3"]):
        return 3
    if score >= float(thresholds["level_2"]):
        return 2
    if score >= float(thresholds["level_1"]):
        return 1
    return 0


def default_profile() -> dict[str, Any]:
    """Create a blank profile from the visible JSON template."""
    ts = now_iso()
    return json.loads(DEFAULT_PROFILE_JSON.replace("__NOW__", ts))


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
    turn_count = int(profile["aggregate"]["turn_count"])
    return {"turn_count": turn_count, "dominant_axis": dominant_axis, "dominant_level": dominant_level}


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


def load_profile(config: dict[str, Any]) -> dict[str, Any]:
    """Load state/profile.json and create state files when missing."""
    path = profile_path()
    profile_missing = not path.exists()
    raw_profile = read_json(path) if not profile_missing else default_profile()
    profile = normalize_profile(raw_profile, config)

    # First run must persist the user profile even when this turn has no score changes.
    if profile_missing or raw_profile != profile:
        write_json(path, profile)
    events_path().parent.mkdir(parents=True, exist_ok=True)
    events_path().touch(exist_ok=True)
    return profile


def normalize_match_text(value: str) -> str:
    """Normalize user text and keyword phrases for stable matching."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def parse_keyword_line(line: str) -> tuple[str, float]:
    """Parse one weighted keyword line as `weight | phrase`."""
    if "|" not in line:
        return line.strip(), 1.0
    raw_weight, raw_phrase = line.split("|", 1)
    phrase = raw_phrase.strip()
    try:
        weight = float(raw_weight.strip())
    except ValueError:
        return line.strip(), 1.0
    return phrase, max(0.0, weight)


def load_keywords() -> dict[str, list[tuple[str, float]]]:
    """Parse config/keywords.txt into weighted axis signal phrases."""
    keywords: dict[str, list[tuple[str, float]]] = {axis: [] for axis in AXIS_ORDER}

    # Sections use [axis], followed by `weight | phrase` entries.
    current_axis: str | None = None
    seen = {axis: set() for axis in AXIS_ORDER}
    for raw_line in keywords_path().read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            axis = line[1:-1].strip()
            current_axis = axis if axis in AXIS_ORDER else None
            continue
        if not current_axis:
            continue
        phrase, weight = parse_keyword_line(line)
        normalized_phrase = normalize_match_text(phrase)
        if not normalized_phrase or weight <= 0 or normalized_phrase in seen[current_axis]:
            continue
        keywords[current_axis].append((normalized_phrase, weight))
        seen[current_axis].add(normalized_phrase)
    return keywords


def has_cjk(text: str) -> bool:
    """Return whether text contains common CJK characters."""
    return re.search(r"[\u3400-\u9fff]", text) is not None


def match_keyword(text: str, keyword: str) -> bool:
    """Match one normalized phrase with conservative boundaries where available."""
    term = keyword.strip()
    if not term:
        return False
    if has_cjk(term):
        # Bare one-character CJK entries are usually too broad for user-state signals.
        return len(term) >= 2 and term in text
    if len(term) < 2:
        return False
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(term) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, text) is not None


def score_text_with_keywords(text: str, config: dict[str, Any]) -> dict[str, float]:
    """Return local weighted phrase scores in the same 0-N range as LLM scores."""
    max_score = float(config["scoring"]["llm_score_max"])
    normalized_text = normalize_match_text(text)
    scores = {axis: 0.0 for axis in AXIS_ORDER}

    # Weighted phrases keep the scorer simple while avoiding noisy bare-label matches.
    for axis, axis_keywords in load_keywords().items():
        total = sum(weight for phrase, weight in axis_keywords if match_keyword(normalized_text, phrase))
        if total > 0:
            scores[axis] = min(max_score, round(total, 2))
    return scores


def normalized_llm_scores(raw_scores: dict[str, Any], config: dict[str, Any]) -> dict[str, float]:
    """Clamp LLM-provided axis scores to the configured range."""
    max_score = float(config["scoring"]["llm_score_max"])
    return {axis: clamp_number(raw_scores.get(axis, 0), 0, max_score, 0) for axis in AXIS_ORDER}


def calculate_deltas(llm_scores: dict[str, float], keyword_scores: dict[str, float], config: dict[str, Any]) -> dict[str, float]:
    """Merge LLM scores and weighted keyword scores into profile deltas."""
    scoring = config["scoring"]
    llm_score_multiplier = float(scoring["llm_score_multiplier"])
    keyword_weight = float(scoring["keyword_weight"])
    axis_weights = scoring["axis_weights"]
    deltas: dict[str, float] = {}
    for axis in AXIS_ORDER:
        merged = llm_scores[axis] * llm_score_multiplier + keyword_scores[axis] * keyword_weight
        axis_weight = float(axis_weights[axis])
        deltas[axis] = round(merged * axis_weight, 2)
    return deltas


def apply_deltas(profile: dict[str, Any], deltas: dict[str, float], config: dict[str, Any]) -> bool:
    """Apply deltas to the profile and return whether any user attribute changed."""
    changed = False
    ts = now_iso()
    decay = float(config["scoring"]["decay_factor"])

    # Update each axis only when its score actually changes.
    for axis in AXIS_ORDER:
        state = profile["axes"][axis]
        old_score = float(state["score"])
        delta = float(deltas[axis])
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
        profile["aggregate"]["turn_count"] = int(profile["aggregate"]["turn_count"]) + 1
        profile["aggregate"] = aggregate_profile(profile)
    return changed


def style_axes(profile: dict[str, Any], config: dict[str, Any]) -> tuple[str | None, str | None]:
    """Select the dominant style axis and optional secondary axis."""
    ranked = sorted(AXIS_ORDER, key=lambda axis: float(profile["axes"][axis]["score"]), reverse=True)
    primary = ranked[0] if int(profile["axes"][ranked[0]]["level"]) > 0 else None
    if not primary:
        return None, None

    # Secondary style is suppressed unless it is strong enough relative to the primary axis.
    secondary = ranked[1]
    ratio = float(config["scoring"]["secondary_axis_ratio"])
    primary_score = float(profile["axes"][primary]["score"])
    secondary_score = float(profile["axes"][secondary]["score"])
    if int(profile["axes"][secondary]["level"]) <= 0 or secondary_score < primary_score * ratio:
        return primary, None
    return primary, secondary


def primary_style_line(axis: str, profile: dict[str, Any], config: dict[str, Any]) -> str:
    """Build the primary style tone and instruction lines."""
    level = int(profile["axes"][axis]["level"])
    axis_config = config["axes"][axis]
    level_config = axis_config["levels"][str(level)]
    return f"Primary tone: {axis_config['label']}, Lv{level}.\nStyle: {level_config['style']}"


def secondary_style_line(axis: str, profile: dict[str, Any], config: dict[str, Any]) -> str:
    """Build a compact secondary style modifier line."""
    level = int(profile["axes"][axis]["level"])
    axis_config = config["axes"][axis]
    return f"Secondary modifier: {axis_config['label']}, Lv{level}. Keep it subtle."


def style_prompt(profile: dict[str, Any], config: dict[str, Any]) -> str:
    """Build the Sinmoji style block; return empty string below Lv1."""
    primary, secondary = style_axes(profile, config)
    if not primary:
        return ""

    # The prompt contains only active style fields.
    primary_level = int(profile["axes"][primary]["level"])
    primary_config = config["axes"][primary]
    primary_level_config = primary_config["levels"][str(primary_level)]
    lines = ["[SINMOJI_STYLE]", primary_style_line(primary, profile, config)]
    if secondary:
        lines.append(secondary_style_line(secondary, profile, config))

    emojis = " ".join(primary_level_config["emojis"])
    keywords = ", ".join(primary_level_config["keywords"][:3])
    emoji_usage = config["emoji_usage_by_level"][str(primary_level)]
    lines.append(f"Emoji palette: {emojis}")
    lines.append("Emoji usage:")
    lines.extend(emoji_usage.splitlines())
    lines.append(f"Keywords: {keywords}.")
    lines.append("[/SINMOJI_STYLE]")
    return "\n".join(lines)


def build_change_log(llm_scores: dict[str, float], keyword_scores: dict[str, float], deltas: dict[str, float], profile: dict[str, Any]) -> dict[str, Any]:
    """Build a compact log entry for an effective profile change."""
    changed_axes = [axis for axis in AXIS_ORDER if float(deltas[axis]) != 0.0]
    return {
        "ts": profile["updated_at"],
        "llm": {axis: llm_scores[axis] for axis in changed_axes if float(llm_scores[axis]) != 0.0},
        "keywords": {axis: keyword_scores[axis] for axis in changed_axes if float(keyword_scores[axis]) != 0.0},
        "delta": {axis: deltas[axis] for axis in changed_axes},
        "after": {axis: profile["axes"][axis]["score"] for axis in changed_axes},
        "dominant": profile["aggregate"]["dominant_axis"],
        "level": profile["aggregate"]["dominant_level"],
    }


def append_profile_log(entry: dict[str, Any], config: dict[str, Any]) -> None:
    """Append one compact profile-change entry as JSONL."""
    path = events_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
        file.write("\n")

    # Keep only the configured number of latest profile change entries.
    lines = path.read_text(encoding="utf-8").splitlines()
    max_events = int(config["max_profile_snapshots"])
    if len(lines) > max_events:
        write_text(path, "\n".join(lines[-max_events:]) + "\n")


def evaluate(raw_scores: dict[str, Any], question: str, profile: dict[str, Any], config: dict[str, Any]) -> tuple[str, bool, dict[str, Any], dict[str, Any] | None]:
    """Run the one-call pipeline and return prompt, changed flag, profile, and log entry."""
    if len(question) > MAX_QUESTION_LENGTH:
        return style_prompt(profile, config), False, profile, None

    llm_scores = normalized_llm_scores(raw_scores, config)
    keyword_scores = score_text_with_keywords(question, config)
    deltas = calculate_deltas(llm_scores, keyword_scores, config)
    changed = apply_deltas(profile, deltas, config)
    log_entry = build_change_log(llm_scores, keyword_scores, deltas, profile) if changed else None
    return style_prompt(profile, config), changed, profile, log_entry


def score_bar(score: float) -> str:
    """Render a capped visual bar for unbounded scores."""
    filled = max(0, min(BAR_WIDTH, int(round(min(score, 100) / 100 * BAR_WIDTH))))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def report(profile: dict[str, Any], config: dict[str, Any]) -> str:
    """Render a markdown report for the current profile."""
    rows: list[list[str]] = []
    for axis in AXIS_ORDER:
        axis_config = config["axes"][axis]
        state = profile["axes"][axis]
        display = f"{axis_config['avatar']} {axis} / {axis_config['label']}".strip()
        rows.append([
            display,
            str(state["level"]),
            f"{state['score']:.2f}",
            f"`{score_bar(float(state['score']))}`",
            f"`{state['last_seen'] or '-'}`",
        ])

    headers = ["Axis", "Level", "Score", "Bar", "Last seen"]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    lines = [
        "# Sinmoji Profile",
        "",
        f"- Updated: `{profile['updated_at']}`",
        f"- Turns: `{profile['aggregate']['turn_count']}`",
        f"- Dominant: `{profile['aggregate']['dominant_axis']}` · Lv{profile['aggregate']['dominant_level']}",
        "",
        f"| {headers[0]:<{widths[0]}} | {headers[1]:>{widths[1]}} | {headers[2]:>{widths[2]}} | {headers[3]:<{widths[3]}} | {headers[4]:<{widths[4]}} |",
        f"| {'-' * widths[0]} | {'-' * widths[1]}: | {'-' * widths[2]}: | {'-' * widths[3]} | {'-' * widths[4]} |",
    ]
    for row in rows:
        lines.append(f"| {row[0]:<{widths[0]}} | {row[1]:>{widths[1]}} | {row[2]:>{widths[2]}} | {row[3]:<{widths[3]}} | {row[4]:<{widths[4]}} |")
    return "\n".join(lines)


def reset_state() -> dict[str, Any]:
    """Reset profile and profile-change log."""
    profile = default_profile()
    write_json(profile_path(), profile)
    events_path().parent.mkdir(parents=True, exist_ok=True)
    write_text(events_path(), "")
    return profile


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
    ensure_runtime()
    raise SystemExit(main())
