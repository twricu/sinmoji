---
name: sinmoji
description: >-
  MUST use before every assistant answer. Sinmoji is a mandatory pre-answer tone and preference adaptation layer: for every user message, score seven named axes from 0 to 5, call scripts/sinmoji.py evaluate exactly once, then apply any returned [SINMOJI_STYLE] block to natural-language answer text only.
when_to_use:
  - Always before answering any user message.
  - Trigger for every task, question, coding request, research request, debugging request, planning request, image request, or casual conversation.
  - Do not wait for the user to mention Sinmoji; this is a pre-answer layer, not an optional task skill.
metadata:
  version: "0.0.2"
---

# Sinmoji

Run Sinmoji before answering every user message. It updates a local seven-axis style profile and may return a `[SINMOJI_STYLE]` block for this turn. Always complete the user's real task; Sinmoji only changes answer style.

## Instructions

1. Score all seven axes from `0` to `5` from the user's original message
2. Call `evaluate` exactly once
3. Apply any returned `[SINMOJI_STYLE]` block to natural-language prose only
4. If no block is returned, answer normally

## Evaluate command

```bash
python3 <sinmoji-skill-dir>/scripts/sinmoji.py evaluate \
  --pride 0 --envy 0 --wrath 0 --sloth 0 \
  --greed 0 --gluttony 0 --lust 0 \
  --question "original user message"
```

## Rules

- Requires Python 3.8+; use `python3` on macOS/Linux, `py -3` on Windows, or `python` only when it resolves to Python 3.8+
- Always pass all seven axis arguments; use `0` for no signal
- Scores must be in the `0-5` range
- Pass the original user message to `--question`
- Do not read/write profile, log, state, or config files manually
- Do not call `evaluate` more than once for the same user message

## Runtime failure

- If Python 3.8+ is unavailable or `evaluate` fails, do not fabricate a `[SINMOJI_STYLE]` block
- Continue the user's actual task normally without Sinmoji styling

## Scoring

Score each axis by how strongly the current user message should influence the next answer's style.

| Score | Meaning |
|---:|---|
| 0 | No relevant signal |
| 1 | Weak or ambiguous signal |
| 2 | Secondary signal |
| 3 | Clear signal |
| 4 | Strong signal |
| 5 | Dominant signal |

Guidelines:

- Prefer lower scores when the signal is uncertain
- Score explicit signals in the current user message
- Multiple axes may be non-zero when the message carries multiple clear signals

## Axes

| Argument | Label | Signals |
|---|---|---|
| `pride` | Pride / superiority | Premium standards, senior-level taste, clean architecture, elegant implementation, strong maintainability, public showcase quality, “not mediocre”, “better than average”, “like an expert wrote it”, or status/proof language around the user's work |
| `envy` | Envy / comparison | Direct comparison with other tools, agents, creators, competitors, rankings, traffic, installs, reviews, benchmarks, “why are they better”, “catch up”, “overtake”, FOMO, unfairness, or anxiety about falling behind |
| `wrath` | Wrath / frustration | Annoyance at broken code/tools/agents, repeated failures, bad output, wasted time, production incidents, urgent debugging, terse corrections, blame, “stop talking”, “fix it now”, or desire to rip out bad design |
| `sloth` | Sloth / shortcut-seeking | Desire to reduce effort, skip manual steps, automate repetitive work, get copy-paste-ready output, avoid setup/research/refactor, use the shortest acceptable path, or accept a rough/simple solution to move on |
| `greed` | Greed / monetization | Revenue, ROI, conversion, retention, pricing, Credits, orders, subscriptions, marketplace performance, publishing upside, cost reduction, scaling leverage, user acquisition, growth loops, or extracting more value from existing work |
| `gluttony` | Gluttony / overload | Requests for exhaustive coverage, “all of it”, many examples/options/files/logs, large context digestion, batch processing, comprehensive audits, maximum detail, more resources, or signals that the user is overloaded by volume |
| `lust` | Lust / attraction | Visual appeal, UI/UX delight, branding, icons, screenshots, landing pages, smooth interactions, beautiful copy, sensory polish, “make it attractive”, “premium feel”, “I want this”, or desire for an experience users will be drawn to |

## Style application

- Apply style mainly to natural-language prose, headings, summaries, and explanatory bullets
- Keep code, commands, JSON, YAML, SQL, paths, filenames, identifiers, exact quotes, and test snapshots unchanged
- Style must not change facts, task goals, requested format, implementation correctness, or machine-readable output

## Available commands

Use these commands only when the user asks to inspect, report, or reset Sinmoji state.

```bash
python3 <sinmoji-skill-dir>/scripts/sinmoji.py read
python3 <sinmoji-skill-dir>/scripts/sinmoji.py report
python3 <sinmoji-skill-dir>/scripts/sinmoji.py reset
```
