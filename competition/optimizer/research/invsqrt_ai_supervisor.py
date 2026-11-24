"""K196 autonomous bounded search with optional Ollama strategy supervisor.

AI chooses only among preapproved deterministic experiments; it never writes
candidate circuits or overrides exact/official verification. Resume-safe.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

SOURCE_SHA = "d7da8646fc6bef7a08f62f8039829fdc3a2669c9572aabf7936596d3ea6560e8"
MODULES = {
    "symbolic": "competition.optimizer.research.invsqrt_symbolic_predicates",
    "diagonal": "competition.optimizer.research.invsqrt_predicate_share",
}
PLANS = [
    {"kind": "symbolic", "span": span, "stride": stride, "passes": passes, "max_wires": width}
    for span in (24, 32, 48, 64, 96, 128, 192, 256)
    for stride in (1, 4, 8, 16)
    for passes in (1, 3)
    for width in (6, 8, 10)
    if stride <= span
] + [
    {"kind": "diagonal", "span": span, "passes": passes}
    for span in (16, 32, 64, 128, 256)
    for passes in (1, 3, 6)
]


def ollama_choice(endpoint, model, remaining, history, timeout):
    prompt = (
        "You supervise an exact quantum circuit optimization search. "
        "Choose ONE integer index from the candidate strategies. "
        "The last searches found no improvements. Prioritize coverage and "
        "novel parameter combinations, not repetition. "
        "Reply with only the integer index. No code.\n"
        + json.dumps({"choices": remaining[:24], "recent": history[-8:]})
    )
    data = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.2, "num_predict": 20}}).encode()
    req = Request(endpoint.rstrip("/") + "/api/generate", data=data,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            result = json.load(response)
        index = int(result.get("response", "").strip())
        if 0 <= index < min(24, len(remaining)):
            return index, "ollama"
    except (ValueError, KeyError, TimeoutError, OSError, URLError):
        pass
    return 0, "fallback"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--campaign-db", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--hours", type=float, default=4)
    p.add_argument("--model", default="llama3.2")
    p.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    p.add_argument("--job-seconds", type=int, default=300)
    p.add_argument("--seed", type=int, default=195)
    a = p.parse_args()
    if not 0 < a.hours <= 24 or not 10 <= a.job_seconds <= 3600:
        p.error("hours must be 0..24, job-seconds 10..3600")
    if hashlib.sha256(a.source.read_bytes()).hexdigest() != SOURCE_SHA:
        p.error("Source SHA mismatch; refusing to optimize an unpinned baseline")
    a.out.mkdir(parents=True, exist_ok=True)
    if a.source.resolve().is_relative_to(a.out.resolve()):
        p.error("Output directory cannot contain immutable source")
    if not a.campaign_db.is_file():
        p.error("Campaign database missing")
    state_path = a.out / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {
        "source_sha256": SOURCE_SHA, "completed": [], "history": [], "best": None}
    if state["source_sha256"] != SOURCE_SHA:
        p.error("Resume state source mismatch")
    rng = random.Random(a.seed)
    plans = list(PLANS)
    rng.shuffle(plans)
    started = time.monotonic()
    deadline = started + a.hours * 3600
    try:
        while time.monotonic() < deadline:
            completed = set(state["completed"])
            remaining = [x for x in plans if json.dumps(x, sort_keys=True) not in completed]
            if not remaining:
                print("SEARCH_SPACE_EXHAUSTED", len(completed), flush=True)
                break
            choice, supervisor = ollama_choice(a.ollama_url, a.model, remaining,
                                               state["history"], 20)
            plan = remaining[choice]
            key = json.dumps(plan, sort_keys=True)
            run_id = hashlib.sha256(key.encode()).hexdigest()[:16]
            folder = a.out / "trials" / run_id
            folder.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, "-m", MODULES[plan["kind"]],
                   "--source", str(a.source.resolve()),
                   "--campaign-db", str(a.campaign_db.resolve()),
                   "--out", str(folder)]
            for k, v in plan.items():
                if k != "kind":
                    cmd += ["--" + k.replace("_", "-"), str(v)]
            allowed = int(min(a.job_seconds, deadline - time.monotonic()))
            if allowed < 10:
                break
            print("K196_START", run_id, supervisor, json.dumps(plan), flush=True)
            start = time.monotonic()
            try:
                with (folder / "worker.log").open("w") as log:
                    proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                                          timeout=allowed, check=False,
                                          env={**os.environ, "OPENBLAS_NUM_THREADS": "1",
                                               "OMP_NUM_THREADS": "1"})
                status = "OK" if proc.returncode == 0 else "ERROR"
            except subprocess.TimeoutExpired:
                status = "TIMEOUT"
            receipt = folder / "report.json"
            result = json.loads(receipt.read_text()) if status == "OK" and receipt.exists() else {}
            record = {"id": run_id, "plan": plan, "status": status,
                      "seconds": round(time.monotonic()-start, 2),
                      "rewrites": result.get("rewrites", 0),
                      "official_status": result.get("official_status", "NOT_RUN"),
                      "verified_improvement": result.get("verified_improvement", False)}
            state["completed"].append(key)
            state["history"].append(record)
            if record["verified_improvement"]:
                state["best"] = {"run_id": run_id, "candidate": result.get("candidate"),
                                 "official_result": result.get("official_verifier_result")}
            temp = state_path.with_suffix(".tmp")
            temp.write_text(json.dumps(state, indent=2) + "\n")
            temp.replace(state_path)
            print("K196_RESULT", json.dumps(record), flush=True)
            if state["best"]:
                print("VERIFIED_IMPROVEMENT", json.dumps(state["best"]), flush=True)
                break
    except KeyboardInterrupt:
        print("INTERRUPTED; completed trials are saved", flush=True)
    print("K196_SUMMARY", json.dumps({
        "completed": len(state["completed"]), "best": state["best"],
        "elapsed_seconds": round(time.monotonic()-started, 1)}), flush=True)


if __name__ == "__main__":
    main()
