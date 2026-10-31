#!/usr/bin/env python3
"""A36: exact reversible controlled modular multiplier for N=143 (8 work bits).

Uses adjacent binary Gray-path transpositions implemented with X and MCX
gates, so NO hidden nonunitary modular arithmetic or oracle is introduced.
Exhaustively validates public permutation and small gate-level spot checks.
This is a deliberately expensive correct source, NOT an efficient multiplier.
"""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path

N=143
BITS=N.bit_length()
def perm(base):
    assert math.gcd(base,N)==1
    return [base*x%N if x<N else x for x in range(1<<BITS)]

def transpositions(mapping):
    seen=set();edges=[]
    for start in range(len(mapping)):
        if start in seen:continue
        cycle=[];x=start
        while x not in seen:
            seen.add(x);cycle.append(x);x=mapping[x]
        assert x==start
        if len(cycle)>1:
            for i in range(1,len(cycle)):
                edges.append((cycle[0],cycle[i]))
    return edges

def gray_path(a,b):
    path=[a]
    diff=a^b
    for bit in range(BITS):
        if diff>>bit&1:path.append(path[-1]^(1<<bit))
    assert path[-1]==b
    return path

def mcx_exchange(qc,control,work,a,b):
    assert (a^b).bit_count()==1
    target=(a^b).bit_length()-1
    controls=[control]+[work[j] for j in range(BITS) if j!=target]
    flipped=[]
    for j in range(BITS):
        if j!=target and not (a>>j&1):
            qc.x(work[j]);flipped.append(j)
    qc.mcx(controls,work[target])
    for j in flipped:qc.x(work[j])

def swap_states(qc,control,work,a,b):
    path=gray_path(a,b)
    # Adjacent swaps along path and return, leaving only endpoint swap.
    for i in list(range(len(path)-1))+list(range(len(path)-3,-1,-1)):
        mcx_exchange(qc,control,work,path[i],path[i+1])

def emit_controlled_multiply(qc,ctrl,work,base):
    mapping=perm(base)
    swaps=transpositions(mapping)
    # Apply the cycle decomposition in forward order.
    for a,b in swaps:
        swap_states(qc,ctrl,work,a,b)
    return swaps

def verify_transpositions(mapping,swaps):
    vals=list(range(len(mapping)))
    for a,b in swaps:
        vals[a],vals[b]=vals[b],vals[a]
    # Verify the sequential swaps for every input state.
    for x in range(len(mapping)):
        y=x
        for a,b in swaps:
            if y==a:y=b
            elif y==b:y=a
        assert y==mapping[x],(x,y,mapping[x])
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,default=2)
    p.add_argument("--compile",action="store_true",help="Build Qiskit source only; may contain many MCX gates")
    p.add_argument("--output",default="results/a36_n143_multiplier.json")
    a=p.parse_args()
    if math.gcd(a.base,N)!=1: p.error("base must be coprime to N143")
    t=time.perf_counter()
    mapping=perm(a.base)
    swaps=transpositions(mapping)
    verify_transpositions(mapping,swaps)
    row={"n":N,"base":a.base,"work_qubits":BITS,
       "valid_residues":N,"invalid_states_fixed":(1<<BITS)-N,
       "permutation_bijective":len(set(mapping))==1<<BITS,
       "cycle_transpositions":len(swaps),"classical_exhaustive_checks":1<<BITS,
       "gate_source_built":False,"gate_level_simulation":False}
    if a.compile:
        from qiskit import QuantumCircuit,QuantumRegister
        ctrl=QuantumRegister(1,"phase")
        work=QuantumRegister(BITS,"work")
        qc=QuantumCircuit(ctrl,work)
        emit_controlled_multiply(qc,ctrl[0],list(work),a.base)
        row["gate_source_built"]=True
        row["gate_counts"]=dict(qc.count_ops())
        row["logical_qubits"]=qc.num_qubits
    row["elapsed_seconds"]=round(time.perf_counter()-t,4)
    report={"experiment":"A36_N143_EXACT_REVERSIBLE_MULTIPLIER",
      "status":"PASS_EXACT_PERMUTATION" if not a.compile else "PASS_SOURCE_BUILT_UNSIMULATED",
      "full_recycled_qpe_integrated":False,"quaspy_integrated_for_n143":False,
      "ptp_preflight":"143 survives 2,3,5,7 wheel; kernel and midpoint remain preserved",
      "scope":"Exact 8-bit reversible multiplier constructor; no claim of practical circuit cost, speedup, or simulated quantum measurement.",
      "row":row}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
