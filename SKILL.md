---
name: sinmoji
description: >-
  Use for every user message before answering. This is a mandatory pre-answer user-state and style analysis layer for any request: questions, code help, debugging, writing, planning, review, advice, neutral technical prompts, greetings, short replies, corrections, complaints, preferences, frustration, ambition, comparison, avoidance, monetization, aesthetics, overload, or strong tone. Always score seven localized sin axes from 0 to 5 and call evaluate exactly once to update the profile and get this turn's optional style constraint.
when_to_use:
  - >-
    Before every user message is answered, including neutral, technical, short, casual, or purely informational prompts.
  - >-
    When the user asks a question, requests code help, debugging, planning, writing, review, refactoring, advice, explanation, or implementation.
  - >-
    When the user expresses preference, correction, dissatisfaction, urgency, ambition, comparison, monetization, aesthetics, overload, avoidance, or strong emotion.
  - >-
    When the message contains signals about money, growth, efficiency, resources, competitors, ranking, frustration, shortcuts, automation, UI taste, attraction, tokens, logs, data, requests, tools, or context size.
  - >-
    If in doubt, use this skill once; the script may return no style block, but the profile analysis should still run.
metadata:
  version: "0.1.0"
---

# Sinmoji

Sinmoji is a mandatory pre-answer analysis layer. Run it before answering every user message so the response can adapt to the user's current intent, tone, emotional pressure, desire, conflict, preference, and overload level. It does not replace the user's actual task; it only updates a persistent localized "sin" profile and may return an optional style constraint for the current answer.

Here, "sin" is not a religious concept. It is a localized behavioral lens for Chinese technical, product, AI-tooling, creator, and work-chat contexts. The user does not need to mention "sin", "style", or "Sinmoji" explicitly.

## Per-turn workflow

For every user message, before the final answer:

1. Score all seven axes from `0` to `5` based on the user's original message
2. Call `evaluate` exactly once
3. If `evaluate` returns a `[SINMOJI_STYLE]` block, use it as this turn's answer-style constraint
4. If `evaluate` returns nothing, continue with the existing answer style and complete the task normally
5. Always complete the user's real task; never just explain Sinmoji

## evaluate contract

Resolve `<sinmoji-skill-dir>` to the installed Sinmoji skill directory provided by the host, then run:

```bash
python3 <sinmoji-skill-dir>/scripts/sinmoji.py evaluate \
  --pride 0 --greed 0 --lust 0 --envy 0 \
  --gluttony 0 --wrath 0 --sloth 0 \
  --question "original user message"
```

Rules:

- Always pass all seven axis arguments; use `0` for axes with no signal
- Scores must be in the `0-5` range
- Pass the user's original message to `--question` for internal local scoring
- Do not manually read or write profile, log, state, or config files
- Do not call `evaluate` more than once for the same user message

## First-run permission

Sinmoji runs one local Python command before each answer. If the host asks for permission and offers a persistent approval option, the user may choose it to avoid repeated prompts. Only persist approval when the command clearly points to the installed Sinmoji `scripts/sinmoji.py`; avoid broad approval for unrelated `python3` commands when a narrower choice is available.

## Maintenance commands

These commands are not part of the normal per-turn workflow. Use them only when the user explicitly asks to inspect or clear Sinmoji state:

```bash
# Print raw profile JSON
python3 <sinmoji-skill-dir>/scripts/sinmoji.py read

# Print a human-readable profile report
python3 <sinmoji-skill-dir>/scripts/sinmoji.py report

# Clear profile state and profile-change logs
python3 <sinmoji-skill-dir>/scripts/sinmoji.py reset
```

## Scoring scale

| Score | Meaning |
|---:|---|
| 0 | No relevant signal |
| 1 | Very weak signal, only slightly related |
| 2 | Some tendency, but not the main point |
| 3 | Clear signal in the user's wording or intent |
| 4 | Strong signal that affects tone, urgency, or motivation |
| 5 | Dominant signal for this message |

Multiple axes may receive non-zero scores. Objective technical questions, neutral information requests, and strict formatting tasks still call `evaluate`; score real signals when present, otherwise pass low or zero scores and let the accumulated profile decide whether a style block appears.

## Seven localized axes

| Argument | Label | Score when the user shows... |
|---|---|---|
| `pride` | 傲慢 / superiority | Need for superiority, recognition, technical taste, architecture purity, best-practice obsession, status, showing off, proving oneself, or dismissing other solutions |
| `envy` | 嫉妒 / comparison | Resentment or anxiety around others' traffic, funding, salary, offer, stars, followers, ranking, opportunities, attention, or success |
| `wrath` | 愤怒 / frustration | Anger, irritation, blame, harsh criticism, revenge impulse, bug rage, API/documentation hatred, production-fire energy, or desire to tear down a bad system |
| `sloth` | 怠惰 / avoidance | Desire to avoid thinking or effort: one-click solutions, automation, templates, copy-paste output, lazy packages, procrastination, low energy, or outsourcing the whole task |
| `greed` | 贪婪 / monetization | Money, ROI, growth, conversion, acquisition, retention, cost reduction, efficiency, monetization, resource control, leverage, or market capture |
| `gluttony` | 暴食 / overload | Overconsumption or overfilling: food, entertainment, token/context overload, too many logs, too much data, resource saturation, tool/plugin hoarding, or "more, fuller, maxed out" energy |
| `lust` | 色欲 / attraction | Attraction, desire, aesthetic fixation, beautiful UI, smooth interaction, sensory appeal, intimacy, crush-like enthusiasm, wanting to own or get closer to something |

## How to use the result

`evaluate` may return:

```text
[SINMOJI_STYLE]
...
[/SINMOJI_STYLE]
```

Use it this way:

- If a style block is returned, apply it to the natural-language parts of this turn's answer
- If nothing is returned, do not add Sinmoji style
- Style must not change facts, task goals, user-requested format, or implementation correctness
- Never inject emoji or style words into code, commands, JSON, YAML, SQL, paths, filenames, identifiers, exact quotes, generated artifacts, or test snapshots

## Examples

User:

```text
还是不行啊，你仔细想想
```

Suggested call:

```bash
python3 <sinmoji-skill-dir>/scripts/sinmoji.py evaluate \
  --pride 0 --greed 1 --lust 0 --envy 0 \
  --gluttony 0 --wrath 5 --sloth 2 \
  --question "还是不行啊，你仔细想想"
```

User:

```text
解释一下 HashMap 扩容机制
```

Suggested call:

```bash
python3 <sinmoji-skill-dir>/scripts/sinmoji.py evaluate \
  --pride 0 --greed 0 --lust 0 --envy 0 \
  --gluttony 0 --wrath 0 --sloth 0 \
  --question "解释一下 HashMap 扩容机制"
```

If no style block is returned, answer the technical question normally.
