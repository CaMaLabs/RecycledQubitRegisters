#!/usr/bin/env python3
"""K183: exact conservative disjoint-commutation CSWAP cancellation.

Only cancels identical CSWAPs when all intervening instructions are unconditional
quantum operations on disjoint qubits. Classical, measurement, conditional,
register, and unknown instructions are barriers. No approximation.
"""
import argparse, collections, hashlib, json, re
from pathlib import Path
SRC=Path("competition/k180/results/helios_const_conditions.kmx")
OUT=Path("competition/k183/results/helios_cswap_cancel.kmx")
REPORT=Path("competition/k183/results/report.json")
Q=re.compile(r"\bq\d+\b")
SAFE={"X","Z","R","Z_POW","NEG","CX","CZ","CCX","CCZ","CSWAP","SWAP"}
def rewrite(lines):
    pending={}; removed=set(); pairs=[]; barriers=collections.Counter()
    for i,line in enumerate(lines):
        s=line.strip(); parts=s.split()
        if not parts: pending.clear();continue
        op=parts[0]
        if op not in SAFE or " if " in s:
            pending.clear();barriers[op]+=1;continue
        qs=frozenset(Q.findall(s))
        if not qs:pending.clear();continue
        if op=="CSWAP" and len(parts)==4:
            key=tuple(parts[1:])
            if key in pending:
                prev=pending[key]
                removed.update((prev,i))
                pairs.append({"first_line":prev+1,"second_line":i+1,"gate":s})
                pending.pop(key)
                # Previous CSWAP is erased; any pending candidate that
                # depended on its qubits was invalidated on first encounter.
                continue
        for key in list(pending):
            if qs.intersection(key):
                del pending[key]
        if op=="CSWAP" and len(parts)==4:
            pending[tuple(parts[1:])]=i
    result=[line for i,line in enumerate(lines) if i not in removed]
    return result, pairs, dict(barriers)
def selftest():
    a=["CSWAP q1 q2 q3","X q4","CSWAP q1 q2 q3"]
    out,p,_=rewrite(a)
    assert out==["X q4"] and len(p)==1
    a=["CSWAP q1 q2 q3","CX q2 q4","CSWAP q1 q2 q3"]
    out,p,_=rewrite(a)
    assert out==a and not p
    a=["CSWAP q1 q2 q3","HMR q4 b1","CSWAP q1 q2 q3"]
    out,p,_=rewrite(a)
    assert out==a and not p
    a=["CSWAP q1 q2 q3","CSWAP q4 q5 q6","CSWAP q1 q2 q3","CSWAP q4 q5 q6"]
    out,p,_=rewrite(a)
    assert not out and len(p)==2
    print("K183_SELFTEST PASS")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--source",type=Path,default=SRC)
    p.add_argument("--output",type=Path,default=OUT)
    args=p.parse_args()
    selftest()
    if args.selftest:return
    data=args.source.read_bytes();lines=data.decode().splitlines(keepends=True)
    result,pairs,barriers=rewrite(lines)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text("".join(result))
    report={"source":str(args.source),"source_sha256":hashlib.sha256(data).hexdigest(),
        "candidate":str(args.output),"candidate_sha256":hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "source_lines":len(lines),"candidate_lines":len(result),"cswap_pairs_cancelled":len(pairs),
        "pairs":pairs,"barriers":barriers,
        "note":"No score gain or semantic correctness claimed without official verification."}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,indent=2)+"\n")
    print("K183_RESULT",json.dumps({k:v for k,v in report.items() if k not in ("barriers",)},sort_keys=True))
if __name__=="__main__":main()
