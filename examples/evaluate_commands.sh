#!/usr/bin/env bash
# Sinmoji manual test commands.
# Usage:
#   bash examples/evaluate_commands.sh 1   # run one case
#   bash examples/evaluate_commands.sh all # run all cases
#   cat examples/evaluate_commands.sh      # copy commands manually

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SINMOJI="$ROOT/scripts/sinmoji.py"

run_case() {
  case "$1" in
    1)
      python3 "$SINMOJI" evaluate --pride 5 --envy 0 --wrath 0 --sloth 0 --greed 0 --gluttony 0 --lust 0 --question "I want the cleanest architecture possible. No mediocre shortcut; make it top-tier."
      ;;
    2)
      python3 "$SINMOJI" evaluate --pride 0 --envy 5 --wrath 0 --sloth 0 --greed 0 --gluttony 0 --lust 0 --question "Their product keeps ranking above ours. I want to benchmark them and find a way to overtake."
      ;;
    3)
      python3 "$SINMOJI" evaluate --pride 0 --envy 0 --wrath 5 --sloth 0 --greed 0 --gluttony 0 --lust 0 --question "This broken API is wasting my time. Stop the bleeding and find the root cause."
      ;;
    4)
      python3 "$SINMOJI" evaluate --pride 0 --envy 0 --wrath 0 --sloth 5 --greed 0 --gluttony 0 --lust 0 --question "Do not optimize or refactor this. Rough is fine; just make it run and skip the polish."
      ;;
    5)
      python3 "$SINMOJI" evaluate --pride 0 --envy 0 --wrath 0 --sloth 0 --greed 5 --gluttony 0 --lust 0 --question "Optimize this for ROI, conversion, cost reduction, and fastest monetization."
      ;;
    6)
      python3 "$SINMOJI" evaluate --pride 0 --envy 0 --wrath 0 --sloth 0 --greed 0 --gluttony 5 --lust 0 --question "Give me the full loaded version with more examples, more resources, and all useful details."
      ;;
    7)
      python3 "$SINMOJI" evaluate --pride 0 --envy 0 --wrath 0 --sloth 0 --greed 0 --gluttony 0 --lust 5 --question "Make the UI feel gorgeous, smooth, delightful, and visually addictive."
      ;;
    8)
      python3 "$SINMOJI" evaluate --pride 3 --envy 0 --wrath 4 --sloth 2 --greed 0 --gluttony 0 --lust 0 --question "This codebase is a mess. Refactor it properly and keep the shortest safe path without sacrificing quality."
      ;;
    9)
      python3 "$SINMOJI" evaluate --pride 0 --envy 3 --wrath 0 --sloth 0 --greed 4 --gluttony 0 --lust 0 --question "Competitors are getting more traffic. Build a growth plan that can catch them and improve revenue."
      ;;
    10)
      python3 "$SINMOJI" evaluate --pride 0 --envy 0 --wrath 0 --sloth 0 --greed 0 --gluttony 0 --lust 0 --question "Explain how HashMap resizing works."
      ;;
    *)
      echo "Unknown case: $1" >&2
      echo "Use: $0 {1..10|all}" >&2
      return 1
      ;;
  esac
}

if [[ "${1:-}" == "all" ]]; then
  for i in {1..10}; do
    printf '\n===== CASE %s =====\n' "$i"
    run_case "$i"
  done
elif [[ -n "${1:-}" ]]; then
  run_case "$1"
else
  echo "Usage: $0 {1..10|all}"
  echo
  echo "Cases:"
  echo "  1  Pride / superiority"
  echo "  2  Envy / comparison"
  echo "  3  Wrath / frustration"
  echo "  4  Sloth / complacency"
  echo "  5  Greed / monetization"
  echo "  6  Gluttony / overload"
  echo "  7  Lust / attraction"
  echo "  8  Pride + wrath + sloth"
  echo "  9  Envy + greed"
  echo "  10 Neutral technical request"
fi
