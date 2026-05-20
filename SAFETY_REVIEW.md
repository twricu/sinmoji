# Safety Review Notes for Sinmoji

Sinmoji is a local response-style adapter packaged as an Agent Skill. It scores seven metaphorical axes before an assistant answer, updates aggregate local state, and may return a `[SINMOJI_STYLE]` block that changes natural-language tone only.

This file is for automated and human safety review. The seven-sins terms are metaphor labels for response style, not instructions to classify protected traits, diagnose users, or bypass platform policy.

## Safety summary

- Style adapter only; not a decision-making authority
- Does not grant or expand tool permissions
- Does not override host platform safety rules
- Must not change facts, code behavior, commands, structured data, or safety policy behavior
- No network clients, telemetry, analytics, webhooks, or outbound API calls
- Raw user messages are not written to Sinmoji profile state or event logs

## Scope

Sinmoji adapts natural-language presentation to the current user message. It may influence tone, directness, detail level, pacing, and aesthetic framing.

Sinmoji is not:

- A psychological assessment or personality test
- A sensitive-attribute classifier
- A protected-trait inference system
- A user risk scoring system
- A safety-policy modifier
- A tool authorization mechanism
- A content policy bypass mechanism

## Axis interpretation and safety boundaries

The names `pride`, `envy`, `wrath`, `sloth`, `greed`, `gluttony`, and `lust` refer to the existing seven-sins cultural model. In Sinmoji they are stable CLI/API names and metaphor labels for style adaptation.

| Axis | Intended style signal | Safety boundary |
|---|---|---|
| `pride` | High standards, polish, professional execution, clean architecture, premium taste | Not moral judgment, superiority claims, narcissism diagnosis, or status-based discrimination |
| `envy` | Comparison pressure, benchmarking, competition, FOMO, ranking anxiety | Not resentment amplification, harassment, unfair targeting, or competitor abuse |
| `wrath` | Urgency, frustration, incident triage, directness, stop-the-bleeding mode | Not threats, harassment, violence, destructive actions, retaliation, or policy bypass |
| `sloth` | Convenience, low-friction workflow, automation, shortcut tolerance, copy-paste readiness | Not negligence, unsafe shortcuts, skipping required validation, or bypassing approvals |
| `greed` | ROI, efficiency, monetization, growth, cost reduction, business outcome focus | Not scams, exploitation, fraud, deceptive growth, or evasion of rules |
| `gluttony` | Fuller coverage, more examples, higher information density, comprehensive context handling | Not data hoarding, privacy invasion, unnecessary collection, or overwhelming unsafe detail |
| `lust` | Aesthetic appeal, visual polish, UI/UX smoothness, desirability of product experience | Not sexual content, sexual profiling, romantic manipulation, or objectification |

## Style-only behavior

Sinmoji output is limited to style guidance for natural-language prose. It must not alter:

- Factual claims
- User task goals
- Code behavior
- Commands
- JSON, YAML, SQL, or other structured data
- Filenames, identifiers, exact quotes, or test snapshots
- Security posture, approval requirements, or safety policy behavior

Host platform safety rules, tool permissions, developer instructions, and explicit user requirements take priority over any Sinmoji style output.

## Scoring boundaries

Scoring should use explicit signals in the current user message. The score is a style cue for the next answer, not a durable judgment about the user.

The assistant should not infer hidden emotions, protected traits, sensitive attributes, medical conditions, psychological diagnoses, or intent that is not present in the message.

## Data handling and privacy

The original user message is passed to the local `evaluate` command for immediate scoring and keyword matching. Raw user messages are not stored in the profile or event log.

Runtime state under the local `state/` directory contains only aggregate numeric scores, levels, timestamps, compact score deltas, and dominant-axis metadata.

Sinmoji does not perform network access, telemetry, analytics, webhook calls, external API calls, advertising attribution, or remote profile synchronization.

## Failure behavior

If Python 3.8+ is unavailable or `evaluate` fails, the assistant must not fabricate a `[SINMOJI_STYLE]` block. The assistant should continue the user's actual task normally without Sinmoji styling.

## Command boundaries

The `evaluate` command is the normal pre-answer path. The `read`, `report`, and `reset` commands are available only when the user asks to inspect, report, or reset Sinmoji state. They should not be run as part of ordinary answers.
