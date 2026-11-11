#!/usr/bin/env python3
"""K112: exact multi-output affine resynthesis of K111 shortlisted windows.

For each K111 directly screened window, simulate every Boolean input of
all its touched wires (<=8). Recover its algebraic normal form and test
whether every output is affine. If so, derive a purely X/CX implementation
with Gaussian elimination. Confirm the entire permutation truth table before
writing any replacement. Never cross unknown/control-flow instructions.

Input K111 must be re-run with --top 200 to include all ~169 candidates.
Only source-level CCX savings are claimed; official Kickmix verifier required.
"""
from __future__ import annotations
import argparse,hashlib,json,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
PAT=re.compile(r'^(X|CX|CCX)\s+((?:q\d+\s*)+)$')
ARITY={"X":1,"CX":2,"CCX":3}

def parse(line):
    m=PAT.fullmatch(line.strip())
    if not m:return None
    op=m.group(1)
    qs=tuple(int(x[1:]) for x in m.group(2).split())
    if len(qs)!=ARITY[op] or len(set(qs))!=len(qs):return None
    return op,qs

def truth(ops,wires):
    k=len(wires)
    idx={wire:j for j,wire in enumerate(wires)}
    output=[]
    for x in range(1<<k):
        v=x
        for op,qs in ops:
            q=tuple(idx[t] for t in qs)
            if op=="X":v^=1<<q[0]
            elif op=="CX":v^=((v>>q[0])&1)<<q[1]
            elif op=="CCX":v^=(((v>>q[0])&1)&((v>>q[1])&1))<<q[2]
        output.append(v)
    return tuple(output)

def affine(table,k):
    bias=table[0]
    cols=[table[1<<i]^bias for i in range(k)]
    for x,y in enumerate(table):
        expected=bias
        for j in range(k):
            if (x>>j)&1:expected^=cols[j]
        if expected!=y:return None
    return bias,cols

def synth_affine(bias,columns,k,wires):
    # Row i is output bit i as XOR of the input bits.
    rows=[sum(((columns[j]>>i)&1)<<j for j in range(k)) for i in range(k)]
    operations=[]
    # Left-multiply A by row-add CNOTs to reach the identity.
    for col in range(k):
        if not (rows[col]&(1<<col)):
            donor=next((r for r in range(col+1,k) if rows[r]&(1<<col)),None)
            if donor is None:raise ValueError("Noninvertible affine permutation")
            rows[col]^=rows[donor]
            operations.append(("CX",donor,col))
        for r in range(k):
            if r!=col and rows[r]&(1<<col):
                rows[r]^=rows[col]
                operations.append(("CX",col,r))
    if rows!=[1<<i for i in range(k)]:raise AssertionError("Gaussian reduction failed")
    # The reduction circuit R satisfies R*A=I, so R^{-1}=A.
    # CNOTs are self-inverse, hence reverse the elimination list.
    output=[]
    for _,control,target in reversed(operations):
        output.append(("CX",(wires[control],wires[target])))
    for i in range(k):
        if (bias>>i)&1:output.append(("X",(wires[i],)))
    return output

def selftest():
    wires=tuple(range(4))
    cases=[
        [("CX",(0,1)),("CX",(1,2)),("X",(3,))],
        [("CCX",(0,1,2)),("CCX",(0,1,2))],
        [("X",(0,)),("CX",(0,3)),("X",(1,))],
    ]
    for ops in cases:
        table=truth(ops,wires)
        params=affine(table,4)
        assert params is not None
        reconstructed=synth_affine(*params,4,wires)
        assert truth(reconstructed,wires)==table
    nonlinear=truth([("CCX",(0,1,2))],wires)
    assert affine(nonlinear,4) is None
    print("K112_SELFTEST PASS 3 affine functions; 1 nonlinear reject",flush=True)

def analyze(record,lines):
    if not record.get("eligible_for_direct_subcircuit_replacement"):return None,"not_direct"
    first=record["start_line"]-1
    last=record["last_line"]
    if first<0 or last>len(lines) or first>=last:return None,"bad_bounds"
    window=lines[first:last]
    ops=[parse(line) for line in window]
    if any(x is None for x in ops):return None,"unsupported_gate"
    wires=tuple(sorted(set(q for _,qs in ops for q in qs)))
    if len(wires)>8 or not wires:return None,"width"
    if len(wires)!=record["touched_width"]:return None,"width_disagree"
    original_ccx=sum(op=="CCX" for op,qs in ops)
    if original_ccx<2:return None,"few_ccx"
    original=truth(ops,wires)
    props=affine(original,len(wires))
    if props is None:return None,"nonlinear"
    replacement=synth_affine(*props,len(wires),wires)
    if truth(replacement,wires)!=original:raise AssertionError("Truth table mismatch")
    candidate_ccx=sum(op=="CCX" for op,qs in replacement)
    if candidate_ccx>=original_ccx:return None,"no_cost_win"
    return {"first_line":first+1,"last_line":last,
            "wires":wires,"original_ccx":original_ccx,
            "replacement_ccx":candidate_ccx,
            "old_size":len(window),"new_size":len(replacement),
            "replacement":[" ".join([op]+[f'q{q}' for q in qs])+"\n" for op,qs in replacement]},None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",type=Path,default=ROOT/"competition/k098/results/helios_immutable.kmx")
    p.add_argument("--k111",type=Path,default=ROOT/"competition/k111/results/small_cone_boundary_audit.json")
    p.add_argument("--out",type=Path,default=ROOT/"competition/k112/results/helios_affine_resynthesis.kmx")
    p.add_argument("--max-rewrites",type=int,default=30)
    a=p.parse_args()
    selftest()
    raw=a.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit("Pinned baseline digest mismatch")
    audit=json.loads(a.k111.read_text())
    if audit.get("sha256")!=sha:raise SystemExit("K111 baseline hash mismatch")
    lines=raw.decode("utf8").splitlines(keepends=True)
    reasons=collections.Counter()
    all_candidates=[]
    for record in audit.get("top",[]):
        result,reason=analyze(record,lines)
        if reason:reasons[reason]+=1
        else:all_candidates.append(result)
    all_candidates.sort(key=lambda r:(-r["original_ccx"],r["new_size"],r["first_line"]))
    selected=[]
    for r in all_candidates:
        if any(r["first_line"]<=x["last_line"] and x["first_line"]<=r["last_line"] for x in selected):
            reasons["overlap"]+=1;continue
        selected.append(r)
        if len(selected)>=a.max_rewrites:break
    output=list(lines)
    for item in sorted(selected,key=lambda r:r["first_line"],reverse=True):
        output[item["first_line"]-1:item["last_line"]]=item["replacement"]
    new="".join(output).encode()
    result={
        "status":"UNVERIFIED_AFFINE_CANDIDATE" if selected else "NO_AFFINE_CANDIDATES",
        "baseline_sha256":sha,"candidate_sha256":hashlib.sha256(new).hexdigest(),
        "k111_records_available":len(audit.get("top",[])),
        "k111_total_candidates":audit.get("candidate_cones"),
        "reasons":dict(reasons),"affine_windows":len(all_candidates),
        "selected_rewrites":len(selected),
        "source_ccx_saved":sum(x["original_ccx"] for x in selected),
        "rewrites":selected,
        "notes":[
            "Only exact affine permutations are replaced by X/CX circuits.",
            "Truth tables exhaustively cover all inputs to each replaced local unitary.",
            "Use K111 --top 200 for full coverage of 169 screened cones.",
            "Source savings are not executed Kickmix cost savings.",
            "Official full-domain verifier required for leaderboard improvement."
        ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.with_suffix(".audit.json").write_text(json.dumps(result,indent=2)+"\n")
    if selected:a.out.write_bytes(new)
    print("K112_COUNTS",json.dumps({k:result[k] for k in (
        "k111_records_available","k111_total_candidates","reasons",
        "affine_windows","selected_rewrites","source_ccx_saved")}),flush=True)
    print("K112_EXAMPLES",json.dumps([{k:r[k] for k in (
        "first_line","last_line","original_ccx","old_size","new_size")}
        for r in selected[:10]]),flush=True)
    print("K112_RESULT",json.dumps({"status":result["status"],
        "audit":str(a.out.with_suffix(".audit.json")),
        "candidate":str(a.out) if selected else None}),flush=True)
if __name__=="__main__":main()
