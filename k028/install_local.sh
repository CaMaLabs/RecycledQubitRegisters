#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$HOME/quantum-a26-check}"
DEST="$ROOT/competition/k028"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -e "$DEST" ]]; then
  echo "Refusing to overwrite existing K028 workspace: $DEST" >&2
  exit 1
fi
mkdir -p "$DEST"
cp "$HERE/native_arithmetic.py" "$HERE/README.md" "$DEST/"
python3 "$DEST/native_arithmetic.py" | tee "$DEST/verified_run.jsonl"
echo "K028 prototype installed at $DEST. K026 remains untouched."
