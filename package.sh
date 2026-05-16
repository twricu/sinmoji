#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v zip >/dev/null 2>&1; then
  echo "error: zip command not found" >&2
  exit 1
fi

VERSION="$(PYTHONIOENCODING=utf-8 python3 -c "import pathlib, re; text = pathlib.Path('SKILL.md').read_text(encoding='utf-8'); match = re.search(r'(?m)^\\s*version:\\s*[\\\"\\']?([^\\\"\\'\\s]+)', text); print(match.group(1) if match else '')")"

if [[ -z "$VERSION" ]]; then
  echo "error: SKILL.md metadata.version not found" >&2
  exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.-]+)?$ ]]; then
  echo "error: invalid version from SKILL.md: $VERSION" >&2
  exit 1
fi

DIST_DIR="dist"
PACKAGE_DIR="sinmoji_v${VERSION}"
STAGING_DIR="$DIST_DIR/$PACKAGE_DIR"
OUTPUT="$DIST_DIR/${PACKAGE_DIR}.zip"
INCLUDES=(
  "SKILL.md"
  "SAFETY_REVIEW.md"
  "agents/openai.yaml"
  "assets/sinmoji-512x512.png"
  "assets/sinmoji-64x64.png"
  "config/keywords.txt"
  "config/sinmoji.json"
  "scripts/sinmoji.py"
)

for path in "${INCLUDES[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "error: required package file missing: $path" >&2
    exit 1
  fi
done

mkdir -p "$DIST_DIR"
rm -rf "$STAGING_DIR"
rm -f "$OUTPUT"

for path in "${INCLUDES[@]}"; do
  mkdir -p "$STAGING_DIR/$(dirname "$path")"
  cp "$path" "$STAGING_DIR/$path"
done

(
  cd "$DIST_DIR"
  zip -qr "${PACKAGE_DIR}.zip" "$PACKAGE_DIR"
)

rm -rf "$STAGING_DIR"

echo "Created $ROOT_DIR/$OUTPUT"
