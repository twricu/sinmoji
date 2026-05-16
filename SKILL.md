---
name: sinmoji
description: >-
  Mandatory pre-answer user-state and style layer. For every user message, score seven Sinmoji axes from 0 to 5, call evaluate exactly once, and apply any returned style block to natural-language answer text only.
when_to_use:
  - Before every user message is answered.
metadata:
  version: "0.0.1"
---

# Sinmoji

Run Sinmoji before answering every user message. It updates a persistent seven-axis profile and may return a `[SINMOJI_STYLE]` block for this turn. Always complete the user's real task; Sinmoji only changes answer style.

## Workflow

1. Score all seven axes from `0` to `5` from the user's original message
2. Call `evaluate` exactly once
3. Apply any returned `[SINMOJI_STYLE]` block to natural-language prose only
4. If no block is returned, answer normally

```bash
python3 <sinmoji-skill-dir>/scripts/sinmoji.py evaluate \
  --pride 0 --envy 0 --wrath 0 --sloth 0 \
  --greed 0 --gluttony 0 --lust 0 \
  --question "original user message"
```

Rules:

- Requires Python 3.8+
- Use `python3` on macOS/Linux; on Windows try `py -3`; use `python` only if it resolves to Python 3.8+
- Always pass all seven axis arguments; use `0` for no signal
- Scores must be in the `0-5` range
- Pass the original user message to `--question`
- Do not read/write profile, log, state, or config files manually
- Do not call `evaluate` more than once for the same user message

Runtime failure:

- If Python is missing, unavailable, or older than 3.8, do not fabricate a `[SINMOJI_STYLE]` block
- Briefly tell the user Sinmoji needs Python 3.8+ and suggest `python3` on macOS/Linux or `py -3` on Windows
- Continue the user's actual task normally without Sinmoji styling

## Scoring

| Score | Meaning |
|---:|---|
| 0 | No relevant signal |
| 1 | Very weak signal |
| 2 | Secondary tendency |
| 3 | Clear signal |
| 4 | Strong signal |
| 5 | Dominant signal |

## Axes

| Argument | Label | Score when the user shows... |
|---|---|---|
| `pride` | Pride / superiority | Exceptional standards, superiority, technical taste, status, showing off, proving oneself, or rejection of mediocre solutions |
| `envy` | Envy / comparison | Rivalry, unfairness, resentment, ranking anxiety, catch-up pressure, or obsession with others' success |
| `wrath` | Wrath / frustration | Irritation, blame, harsh criticism, incident pressure, bug rage, or desire to tear down a bad system |
| `sloth` | Sloth / complacency | Quality apathy, low standards, refusal to optimize/refactor/test/learn, good-enough shortcuts, or willingness to sacrifice maintainability |
| `greed` | Greed / monetization | Money, ROI, growth, conversion, monetization, leverage, resource capture, or market capture |
| `gluttony` | Gluttony / overload | Abundance, overload, maxed-out resources, too much data/context, hoarding, or all-in volume |
| `lust` | Lust / attraction | Aesthetic fixation, attraction, beautiful UI, smooth UX, sensory appeal, desire, or wanting to own/get closer |

Guardrails:

- Do not score `pride` for ordinary correctness, clean code, or professional work alone
- Do not score `envy` for neutral benchmarking or competitor research alone
- Do not score `wrath` for a neutral bug report or error message alone
- Do not score `sloth` just because the user asks for work, automation, templates, or copy-ready output
- Do not score `greed` for generic efficiency or normal budgeting alone
- Do not score `gluttony` for ordinary thoroughness alone

## Applying style

- Apply style only to natural-language prose
- Never put emoji or style words inside code, commands, JSON, YAML, SQL, paths, filenames, identifiers, exact quotes, generated artifacts, or test snapshots
- Style must not change facts, task goals, requested format, or implementation correctness

## Maintenance commands

```bash
python3 <sinmoji-skill-dir>/scripts/sinmoji.py read
python3 <sinmoji-skill-dir>/scripts/sinmoji.py report
python3 <sinmoji-skill-dir>/scripts/sinmoji.py reset
```
