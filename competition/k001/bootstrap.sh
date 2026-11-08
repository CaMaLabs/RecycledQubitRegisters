#!/usr/bin/env bash
# K001: local-only competition bootstrap; NEVER commit official Kaggle assets.
set -Eeuo pipefail
ROOT="$(git rev-parse --show-toplevel)"
DIR="$ROOT/competition/k001"
PRIVATE="$DIR/private"
ARCHIVE="$PRIVATE/downloads/google-verifiable-quantum-circuit-compilation.zip"
REPORT="$DIR/k001_environment_report.json"
mkdir -p "$PRIVATE/downloads" "$PRIVATE/official" "$PRIVATE/metric" "$PRIVATE/runs"
chmod 700 "$PRIVATE"
PY="${PY:-$HOME/ibm-6c2q-venv/bin/python}"
if ! "$PY" -c "import kaggle" >/dev/null 2>&1; then
  "$PY" -m pip install --upgrade kaggle
fi
KAGGLE="$(dirname "$PY")/kaggle"
if [ ! -x "$KAGGLE" ]; then
  KAGGLE="$(command -v kaggle || true)"
fi
if [ -z "$KAGGLE" ] || [ ! -x "$KAGGLE" ]; then
  echo "ERROR: Kaggle CLI missing from Python environment" >&2; exit 1
fi
if [ ! -f "$ARCHIVE" ]; then
  "$KAGGLE" competitions download -c google-verifiable-quantum-circuit-compilation -p "$PRIVATE/downloads"
fi
if [ ! -f "$ARCHIVE" ]; then
  echo "ERROR: Kaggle archive missing; check CLI authentication and competition access" >&2
  exit 1
fi
if [ ! -f "$PRIVATE/official/.k001_extracted" ]; then
  "$PY" -m zipfile -e "$ARCHIVE" "$PRIVATE/official"
  touch "$PRIVATE/official/.k001_extracted"
fi
if [ ! -f "$PRIVATE/metric/.k001_metric_pulled" ]; then
  if "$KAGGLE" kernels pull metric/google-quantum-ai-metric -p "$PRIVATE/metric"; then
    touch "$PRIVATE/metric/.k001_metric_pulled"
  else
    echo "WARNING: metric kernel pull failed; local official verifier assets remain available" >&2
  fi
fi
K001_PRIVATE="$PRIVATE" K001_REPORT="$REPORT" "$PY" - <<'PYCODE'
import hashlib, json, os, platform, sys
from pathlib import Path
private=Path(os.environ["K001_PRIVATE"])
report=Path(os.environ["K001_REPORT"])
files=[]
for base in (private/"official",private/"metric"):
    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.name.startswith(".k001_"):continue
        if len(files)>=2500:break
        files.append({"path":str(p.relative_to(private)),"bytes":p.stat().st_size})
archive=private/"downloads/google-verifiable-quantum-circuit-compilation.zip"
d={"experiment":"K001_OFFICIAL_ASSET_INVENTORY","status":"ASSETS_AVAILABLE",
   "competition_slug":"google-verifiable-quantum-circuit-compilation",
   "python":sys.version.split()[0],"platform":platform.platform(),
   "archive_sha256":hashlib.file_digest(archive.open("rb"),"sha256").hexdigest(),
   "private_assets_kept_out_of_git":True,"file_count_reported":len(files),
   "files":files,
   "notes":["Inventory contains filenames and sizes ONLY, no competition binaries, verifier source, or credentials.",
    "Submission format and circuit representation MUST be inspected locally before building candidates.",
    "No competition submission or quantum hardware execution was performed."]}
report.write_text(json.dumps(d,indent=2)+"\n")
print("K001 STATUS:",d["status"])
print("K001 ASSET COUNT:",len(files))
print("K001 INVENTORY:",report)
for item in files[:70]:print(item["path"],item["bytes"])
PYCODE
echo "K001 bootstrap complete. Official assets remain in ignored private/."
