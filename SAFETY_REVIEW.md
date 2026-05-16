# Safety Review Notes for Sinmoji

Sinmoji is a local response-style adapter. It borrows the well-known seven deadly sins motif as a playful metaphor for style preferences, then scores seven axes, updates aggregate local state, and may return a `[SINMOJI_STYLE]` block that changes only natural-language tone.

## Terminology

The name “Sinmoji” and the axes `pride`, `envy`, `wrath`, `sloth`, `greed`, `gluttony`, and `lust` refer to the existing seven-sins cultural model. In this package they are entertainment-oriented metaphor labels and stable CLI/API names, not moral judgment, psychological diagnosis, sensitive-attribute profiling, or instructions to produce unsafe content.

| Axis | Intended meaning |
|---|---|
| `pride` | Quality standard, polish, professional execution |
| `envy` | Comparison pressure, benchmarking, competitive context |
| `wrath` | Urgency, frustration, direct triage needs |
| `sloth` | Convenience, low-friction workflow, shortcut tolerance |
| `greed` | ROI, efficiency, growth, monetization context |
| `gluttony` | Fuller coverage, more detail, higher information density |
| `lust` | Aesthetics, visual appeal, UI/UX smoothness |

## Safety boundaries

- The skill only changes response style; it must not change facts, task goals, code behavior, commands, JSON/YAML/SQL, filenames, identifiers, or safety policy behavior.
- Host platform safety rules always override Sinmoji style output.
- `lust` is limited to aesthetics and product experience, not sexual content or sexual profiling.
- `wrath` is limited to urgent/direct tone, not threats, harassment, violence, or destructive actions.
- `greed` is limited to business/outcome framing, not scams, exploitation, fraud, or policy evasion.

## Privacy

Sinmoji does not include network clients, telemetry, webhooks, or outbound API calls. Raw user messages are not stored. Runtime state contains only aggregate numeric scores, levels, timestamps, and compact score deltas under the local `state/` directory.
