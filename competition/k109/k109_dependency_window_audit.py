#!/usr/bin/env python3
"""K109: discover safely extractable noncontiguous 3/4-wire reversible windows.

An anchor pair of CCX gates defines fixed support S (up to 4 qubits).
For every intervening instruction:
  - X/CX/CCX wholly in S: include in the candidate subcircuit
  - an explicitly parsed gate entirely outside S: skip (commutes by support)
  - any mixed-support gate, unknown operation, or control-flow line: reject

The resulting projected subcircuit can be commuted together exactly, and
an exact replacement on S can be inserted at its first included operation.
This script performs READ-ONLY discovery, not replacement or proof of
optimality. No unsupported control-flow or phase operation is crossed.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
ARITY={"X":1,"CX":2,"CCX":3,"CCZ":3,"CSWAP":3,"SWAP":2,
       "Z_POW":2}  # Z_POW expects a qubit + angle; special-cased below
PAT=re.compile(r"^([A-Z][A-Z0-9_]*)\s+(.*)$")
Q=re.compile(r"^q(\d+)$")
NUMBER=re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
def classify(line):
    s=line.strip()
    m=PAT.fullmatch(s)
    if not m:return None
    op,args=m.group(1),m.group(2).split()
    if op=="Z_POW" and len(args)==2 and Q.fullmatch(args[0]) and NUMBER.fullmatch(args[1]):
        return op,frozenset([int(args[0][1:])]),False
    if op not in ARITY or op=="Z_POW":return None
    if len(args)!=ARITY[op] or any(Q.fullmatch(t) is None for t in args):return None
    qs=tuple(int(t[1:]) for t in args)
    if len(set(qs))!=len(qs):return None
    return op,frozenset(qs),op in ("X","CX","CCX")
def scan(lines,span,max_results):
    parsed=[classify(line) for line in lines]
    ccx_indices=[i for i,g in enumerate(parsed) if g and g[0]=="CCX"]
    results=[]
    counts=collections.Counter()
    candidate_supports=set()
    for i in ccx_indices:
        left=parsed[i]
        active=left[1]
        for j in ccx_indices:
            if j<=i:continue
            if j-i>span:break
            right=parsed[j]
            support=active|right[1]
            if len(support)>4 or len(support)<3:continue
            candidate_supports.add(tuple(sorted(support)))
            counts["anchor_pairs_with_4_or_fewer_wires"]+=1
            included=[]
            rejected=None
            for k in range(i,j+1):
                g=parsed[k]
                if g is None:
                    rejected="unknown_or_control";break
                _,qs,allowed=g
                if qs.isdisjoint(support):continue
                if qs<=support and allowed:
                    included.append(k);continue
                rejected="mixed_support_or_nonreversible";break
            if rejected:
                counts["rejected_"+rejected]+=1
                continue
            counts["extractable_pairs"]+=1
            selected=[parsed[k][0] for k in included]
            summary={"first_line":i+1,"last_line":j+1,
                     "span_lines":j-i+1,"support":sorted(support),
                     "included_gates":len(included),
                     "skipped_disjoint_gates":j-i+1-len(included),
                     "included_ccx":selected.count("CCX"),
                     "included_cx":selected.count("CX"),
                     "included_x":selected.count("X"),
                     "gate_line_numbers":[k+1 for k in included],
                     "original_instructions":[lines[k].strip() for k in included]}
            results.append(summary)
    results.sort(key=lambda x:(-x["included_ccx"],-x["skipped_disjoint_gates"],
                                x["included_gates"],x["first_line"]))
    unique=[]
    seen=set()
    for r in results:
        key=(tuple(r["support"]),tuple(r["gate_line_numbers"]))
        if key not in seen:
            unique.append(r);seen.add(key)
    return counts,len(candidate_supports),unique[:max_results],len(unique)

def selftest():
    a=["CCX q0 q1 q2\n","CX q7 q8\n","X q3\n","CCX q0 q1 q3\n"]
    c,_,r,_=scan(a,100,5)
    assert c["extractable_pairs"]==1 and r[0]["skipped_disjoint_gates"]==1
    b=["CCX q0 q1 q2\n","CX q2 q5\n","CCX q0 q1 q3\n"]
    c,_,r,_=scan(b,100,5)
    assert c["extractable_pairs"]==0 and c["rejected_mixed_support_or_nonreversible"]==1
    c,_,r,_=scan(["CCX q0 q1 q2\n","PUSH_CONDITION b0\n","CCX q0 q1 q3\n"],100,5)
    assert c["extractable_pairs"]==0 and c["rejected_unknown_or_control"]==1
    print("K109_SELFTEST PASS 3 extraction and barrier cases",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",type=Path,default=ROOT/"competition/k098/results/helios_immutable.kmx")
    p.add_argument("--span",type=int,default=300)
    p.add_argument("--max-results",type=int,default=30)
    p.add_argument("--out",type=Path,default=ROOT/"competition/k109/results/dependency_windows.json")
    a=p.parse_args()
    if a.span<2 or a.max_results<1:p.error("span >=2 and max-results >=1 required")
    selftest()
    raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit("Pinned baseline SHA-256 mismatch")
    lines=raw.decode("utf8").splitlines(keepends=True)
    counts,supports,results,unique=scan(lines,a.span,a.max_results)
    report={"status":"AUDIT_ONLY","source_sha256":sha,
            "span_limit":a.span,"candidate_support_sets":supports,
            "stats":dict(counts),"unique_extractable_windows":unique,
            "top_extractable_windows":results,
            "limitations":[
              "Requires all intervening instructions to have recognized gate syntax.",
              "A window is safely isolated only if its included operations stay on the fixed four-wire support.",
              "Ignored gates must have no wires in common with the chosen support.",
              "Some reversible regions may be missed due to unknown syntax or sparse connectivity.",
              "No rewrites, Kickmix execution, or leaderboard score measured."
            ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print("K109_COUNTS",json.dumps({"support_sets":supports,"unique_windows":unique,
          **dict(counts)}),flush=True)
    for r in results[:10]:
        print("K109_WINDOW",json.dumps({k:r[k] for k in (
          "first_line","last_line","span_lines","support","included_gates",
          "skipped_disjoint_gates","included_ccx","included_cx","included_x")}),flush=True)
    print("K109_RESULT",json.dumps({"status":"AUDIT_ONLY","out":str(a.out),
          "unique_extractable_windows":unique}),flush=True)

if __name__=="__main__":main()
