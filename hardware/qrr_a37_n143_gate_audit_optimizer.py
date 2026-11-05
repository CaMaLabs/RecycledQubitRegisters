#!/usr/bin/env python3
"""A37: exhaustive 512-state gate instruction audit and X-frame optimization.

Reuses the original A36 MCX state swaps without changing their order. Carries
X inversion frames between adjacent MCX instructions rather than unflipping
each time. Simulates EVERY (control, eight-work-bit) basis state through the
actual Qiskit source instructions. No QPU or factor/order oracle.
"""
import argparse,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a36_n143_reversible_multiplier as a36
from qiskit import QuantumCircuit

def optimized_multiply(base):
    qc=QuantumCircuit(9)
    work=list(range(1,9))
    mask=0
    swaps=a36.transpositions(a36.perm(base))
    for left,right in swaps:
        path=a36.gray_path(left,right)
        for idx in list(range(len(path)-1))+list(range(len(path)-3,-1,-1)):
            u,v=path[idx],path[idx+1]
            bit=(u^v).bit_length()-1
            target_mask=sum(1<<j for j in range(8) if j!=bit and not (u>>j&1))
            delta=mask^target_mask
            for j in range(8):
                if delta>>j&1:qc.x(work[j])
            mask=target_mask
            qc.mcx([0]+[work[j] for j in range(8) if j!=bit],work[bit])
    for j in range(8):
        if mask>>j&1:qc.x(work[j])
    return qc

def original_multiply(base):
    qc=QuantumCircuit(9)
    a36.emit_controlled_multiply(qc,0,list(range(1,9)),base)
    return qc

def run_basis(qc,value):
    state=value
    for instruction in qc.data:
        op=instruction.operation
        inds=[qc.find_bit(q).index for q in instruction.qubits]
        if op.name=="x":
            state^=1<<inds[0]
        elif op.name=="mcx":
            if all(state>>i&1 for i in inds[:-1]):
                state^=1<<inds[-1]
        else:
            raise AssertionError("unexpected source gate: "+op.name)
    return state

def verify(qc,base):
    for ctrl in (0,1):
        for y in range(256):
            state=ctrl+(y<<1)
            target=ctrl+((a36.perm(base)[y] if ctrl else y)<<1)
            actual=run_basis(qc,state)
            if actual!=target:
                raise AssertionError(dict(base=base,ctrl=ctrl,input=y,got=actual,expected=target))
    return 512

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bases",nargs="+",type=int,default=[2,8])
    p.add_argument("--output",default="results/a37_exact_gate_optimization.json")
    args=p.parse_args()
    rows=[]
    for base in args.bases:
        if math.gcd(base,143)!=1:p.error("base must be coprime to 143")
        t=time.perf_counter()
        original=original_multiply(base)
        optimized=optimized_multiply(base)
        original_checks=verify(original,base)
        optimized_checks=verify(optimized,base)
        original_counts=dict(original.count_ops())
        optimized_counts=dict(optimized.count_ops())
        row=dict(n=143,base=base,checked_basis_states_each=512,
            original_counts=original_counts,optimized_counts=optimized_counts,
            x_removed=original_counts.get("x",0)-optimized_counts.get("x",0),
            x_reduction_fraction=1-optimized_counts.get("x",0)/max(1,original_counts.get("x",0)),
            mcx_unchanged=original_counts.get("mcx",0)==optimized_counts.get("mcx",0),
            gate_level_basis_checks_pass=True,seconds=round(time.perf_counter()-t,3))
        assert row["mcx_unchanged"] and row["x_removed"]>=0
        rows.append(row)
        print(json.dumps(row),flush=True)
    result={"experiment":"A37_N143_EXHAUSTIVE_GATE_AND_X_FRAME_OPTIMIZATION",
       "status":"PASS_EXACT_512_STATE_GATE_AUDIT_AND_X_OPTIMIZATION",
       "qpu_jobs":0,"n143_recycled_qpe":False,
       "quaspy_n143":False,
       "limitations":"All 512 computational-basis states tested per source; these X/MCX classical-permutation gates cannot establish arbitrary superposition phase behavior beyond their gate semantics. Multi-controlled gate decomposition, placement and native costs not yet tested.",
       "rows":rows}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print("SAVED",out)
if __name__=="__main__":main()
