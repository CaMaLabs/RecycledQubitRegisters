"""K197: historical-branch product-sharing campaign with optional Ollama ranking.

Read-only historical SQLite; immutable source; per-candidate evidence; resumable.
The qrom_products pass uses its existing zero-scratch symbolic proof and the
official campaign verifier remains the only promotion authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from urllib.request import Request, urlopen

from ..autonomous.qrom_products import optimize as qrom_optimize
from ..autonomous.core import sha
from .invsqrt_phase_fit import verify_against_campaign

PIN = "d7da8646fc6bef7a08f62f8039829fdc3a2669c9572aabf7936596d3ea6560e8"


def historical(db, limit):
    with sqlite3.connect("file:" + str(db.resolve()) + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT sha,path,official_status,score FROM candidates "
            "WHERE official_status IN ('NOT_RUN','PASS_FULL','TIMEOUT','BUDGET_EXHAUSTED') "
            "ORDER BY CASE official_status WHEN 'PASS_FULL' THEN 0 ELSE 1 END, "
            "score ASC, created DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def choose(rows, model, endpoint):
    # AI can rank *existing* source candidates, never fabricate circuit content.
    if not model or len(rows) < 2:
        return 0, "deterministic"
    prompt = ("Select one integer index to prioritize for exact reversible "
              "logic product-sharing. Prefer untested diverse branches; "
              "respond with an integer only.\n" +
              json.dumps([{"index": i, "status": r["official_status"],
                           "score": r["score"]} for i,r in enumerate(rows[:12])]))
    request = Request(endpoint.rstrip("/") + "/api/generate",
                      data=json.dumps({"model": model, "prompt": prompt,
                                       "stream": False, "options": {"num_predict": 12,
                                       "temperature": 0.1}}).encode(),
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            n = int(json.load(response)["response"].strip())
        if 0 <= n < min(12, len(rows)):
            return n, "ollama"
    except (OSError, ValueError, KeyError):
        pass
    return 0, "fallback"


def save(path, state):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    tmp.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--campaign-db", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--hours", type=float, default=4)
    p.add_argument("--max-candidates", type=int, default=300)
    p.add_argument("--model", default="")
    p.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    p.add_argument("--verifier-timeout", type=float, default=1800)
    a = p.parse_args()
    if not 0 < a.hours <= 24 or not 1 <= a.max_candidates <= 10000:
        p.error("Invalid campaign limits")
    baseline = a.source.read_bytes()
    if sha(baseline) != PIN:
        p.error("Baseline digest mismatch")
    if a.source.resolve().is_relative_to(a.out.resolve()):
        p.error("Output contains baseline source")
    a.out.mkdir(parents=True, exist_ok=True)
    statefile = a.out / "state.json"
    state = json.loads(statefile.read_text()) if statefile.exists() else {
        "source_sha256": PIN, "completed": {}, "verified_winner": None}
    if state["source_sha256"] != PIN:
        p.error("Resume source mismatch")
    candidates = historical(a.campaign_db, a.max_candidates)
    # Always include the pinned baseline, independent of historical DB entries.
    candidates.insert(0, {"sha": PIN, "path": str(a.source.resolve()),
                          "official_status": "BASELINE", "score": None})
    deadline = time.monotonic() + a.hours * 3600
    while time.monotonic() < deadline:
        available = [r for r in candidates if r["sha"] not in state["completed"]]
        if not available:
            break
        index, supervisor = choose(available[:12], a.model, a.ollama_url)
        record = available[index]
        digest = record["sha"]
        path = Path(record["path"])
        started = time.monotonic()
        outcome = {"parent": digest, "supervisor": supervisor, "status": "SKIPPED"}
        try:
            if not path.is_file():
                outcome["reason"] = "historical candidate path missing"
            else:
                raw = path.read_bytes()
                if sha(raw) != digest:
                    outcome["reason"] = "historical candidate digest mismatch"
                else:
                    child, evidence = qrom_optimize(raw)
                    outcome["proof"] = evidence.get("proof")
                    outcome["static_toffoli_removed"] = evidence.get("static_toffoli_removed")
                    if evidence.get("proof", {}).get("status") != "EXACT":
                        outcome["status"] = "PROOF_REJECT"
                    elif sha(child) == digest:
                        outcome["status"] = "NO_CHANGE"
                    else:
                        childsha = sha(child)
                        folder = a.out / "candidates" / childsha
                        folder.mkdir(parents=True, exist_ok=True)
                        candidate = folder / (childsha + ".kmx")
                        candidate.write_bytes(child)
                        (folder / "local_proof.json").write_text(json.dumps(evidence, indent=2))
                        outcome.update({"status": "LOCAL_IMPROVEMENT", "candidate_sha256": childsha,
                                        "candidate_path": str(candidate)})
                        # Official verification may exceed the remaining time;
                        # do not start a verifier without enough budget.
                        remaining = deadline - time.monotonic()
                        if remaining >= a.verifier_timeout * 2 + 10:
                            report = {"source_sha256": PIN,
                                      "candidate": {"sha256": childsha}}
                            verify_against_campaign(candidate, report, a.campaign_db,
                                                    folder, a.verifier_timeout)
                            outcome["official_status"] = report["official_status"]
                            outcome["verified_improvement"] = report["verified_improvement"]
                            (folder / "official_receipt.json").write_text(json.dumps(report, indent=2))
                            if report["verified_improvement"]:
                                state["verified_winner"] = outcome
                        else:
                            outcome["official_status"] = "DEFERRED_TIME_BUDGET"
        except Exception as exc:
            outcome.update({"status": "ERROR", "reason": repr(exc)})
        outcome["seconds"] = round(time.monotonic() - started, 2)
        state["completed"][digest] = outcome
        save(statefile, state)
        print("K197_RESULT", json.dumps(outcome), flush=True)
        if state["verified_winner"]:
            break
    print("K197_SUMMARY", json.dumps({"completed": len(state["completed"]),
          "verified_winner": state["verified_winner"]}), flush=True)


if __name__ == "__main__":
    main()
