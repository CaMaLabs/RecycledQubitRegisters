#!/usr/bin/env bash
# K146: original upstream Polytof compile -> BCO -> CPD on exactly ONE
# bounded, pinned Helios region. Does not generate/submit Helios rewrites.
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PY="${PY:-$HOME/.venvs/kaggle-k001/bin/python}"
ADAPTER=competition/k146/k146_polytof_adapter.py
OUT=competition/k146/results
mkdir -p "$OUT"
"$PY" "$ADAPTER" --top 8
"$PY" - <<'PY'
import json
d=json.load(open("competition/k146/results/extraction.json"))
if not d["top"]:
 raise SystemExit("K146 NO GO: No supported multi-Toffoli unitary island")
best=d["top"][0]
print("K146_SELECTED", json.dumps(best))
PY
SRC="$("$PY" - <<'PY'
import json
print(json.load(open("competition/k146/results/extraction.json"))["top"][0]["qc"])
PY
)"
UPSTREAM="${POLYTOF_HOME:-$HOME/work/polytof}"
if [[ ! -f "$UPSTREAM/src/compile.cpp" ]]; then
  mkdir -p "$(dirname "$UPSTREAM")"
  git clone --depth 1 https://github.com/ZIB-IOL/polytof.git "$UPSTREAM"
fi
UPSTREAM="$(realpath "$UPSTREAM")"
mkdir -p "$UPSTREAM/bin" "$UPSTREAM/data/circuits/raw" "$OUT"
ID=7145
SHIFTED=8145
if [[ -e "$UPSTREAM/data/circuits/raw/$(printf '%04d' "$ID").qc" ]]; then
  echo "STOP: Upstream raw ID $ID already exists; refusing to overwrite." >&2
  exit 3
fi
cp "$SRC" "$UPSTREAM/data/circuits/raw/$(printf '%04d' "$ID").qc"
(
cd "$UPSTREAM"
[[ -x bin/compile ]] || g++ -O2 -std=c++20 -pthread -I third_party -I src src/compile.cpp -o bin/compile
[[ -x bin/bco ]] || g++ -O2 -std=c++20 -pthread -I third_party -I src src/bco.cpp -o bin/bco
[[ -x bin/topp1 ]] || g++ -D VEC_WORDS=1 -O2 -std=c++20 -pthread -I third_party -I src src/cpd.cpp -o bin/topp1
echo "K146 UPSTREAM COMPILER"
timeout 120 bin/compile "$ID" --idx | tee "$OLDPWD/$OUT/compile.log"
echo "K146 ORIGINAL BCO"
timeout 120 bin/bco "$ID" -b 2 -t 2 --save --verify | tee "$OLDPWD/$OUT/bco.log"
echo "K146 ORIGINAL CPD SGE"
timeout 120 bin/topp1 "$SHIFTED" --sge -b 2 -t 2 --save --verify | tee "$OLDPWD/$OUT/cpd.log"
)
"$PY" - <<'PY'
import json,re
from pathlib import Path
p=Path("competition/k146/results")
logs={k:(p/(k+".log")).read_text() for k in ("compile","bco","cpd")}
c=logs["compile"]
out=re.search(r"output:\s*(\d+) qubits\s*\((\d+) ancillas\)",c)
orig=re.search(r"input:\s*(\d+) qubits",c)
rank=re.search(r"Best rank:\s*(\d+)",logs["cpd"])
report={"status":"UPSTREAM_ANALYSIS_NOT_A_HELIOS_REWRITE",
"original_island_qubits":int(orig.group(1)) if orig else None,
"compiled_qubits":int(out.group(1)) if out else None,
"new_ancillas":int(out.group(2)) if out else None,
"upstream_cpd_best_rank":int(rank.group(1)) if rank else None,
"source_extraction":json.load(open(p/"extraction.json"))["top"][0],
"warning":"No reconstruction, exact channel proof, 62q scoring check or official verifier completed."}
(p/"upstream_trial.json").write_text(json.dumps(report,indent=2)+"\n")
print("K146_UPSTREAM_RESULT",json.dumps(report))
PY
