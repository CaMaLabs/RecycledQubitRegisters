#!/usr/bin/env python3
"""K156 exact X-basis carry cleanup vs Bennett reversal.
Standalone out-of-place modular XOR-adder, not a full Helios candidate.
"""
import argparse, collections, hashlib, json, random
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"

def wires(n):
    return ([i for i in range(n)], [n+i for i in range(n)], [2*n+i for i in range(n)], [3*n+i for i in range(n-1)])

def compose(n):
    if n < 2: raise ValueError("n>=2")
    a,b,z,c = wires(n)
    compute=[("CCX",a[0],b[0],c[0])]
    for i in range(1,n-1):
        compute += [("CCX",a[i],b[i],c[i]),("CX",a[i],b[i]),
                    ("CCX",b[i],c[i-1],c[i]),("CX",a[i],b[i])]
    sums=[]
    for i in range(n):
        sums.extend([("CX",a[i],z[i]),("CX",b[i],z[i])])
        if i>0: sums.append(("CX",c[i-1],z[i]))
    bennett=compute+sums+list(reversed(compute))
    measured=compute+sums
    for i in range(n-2,-1,-1):
        bit=f"m{i+1}"
        measured.append(("HMR",c[i],bit))
        measured.append(("CZ_IF",a[i],b[i],bit))
        if i>0:
            measured.extend([("CX_IF",a[i],b[i],bit),
                             ("CZ_IF",b[i],c[i-1],bit),
                             ("CX_IF",a[i],b[i],bit)])
    return bennett,measured

def play_classical(v,gates):
    for op,*a in gates:
        if op=="CX":v ^= ((v>>a[0])&1)<<a[1]
        elif op=="CCX":v ^= (((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
        else:raise ValueError(op)
    return v

def coherent_phase_branch(v,gates,outcomes):
    # Each HMR X-outcome m gives phase (-1)^(m * current_work_bit);
    # the classical correction must cancel it for EVERY input branch.
    phase=0
    for op,*a in gates:
        if op=="CX":v ^= ((v>>a[0])&1)<<a[1]
        elif op=="CCX":v ^= (((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
        elif op=="HMR":
            q,bit=a
            phase ^= ((v>>q)&1)&outcomes[bit]
            v &= ~(1<<q)
        elif op=="CZ_IF":
            p,q,bit=a
            phase ^= ((v>>p)&1)&((v>>q)&1)&outcomes[bit]
        elif op=="CX_IF":
            p,q,bit=a
            if outcomes[bit]:v ^= ((v>>p)&1)<<q
        else:raise ValueError(op)
    return v,phase

def verify(n,bennett,measured):
    mask=(1<<n)-1
    rng=random.Random(156+n)
    bases=branches=0
    for av in range(1<<n):
        for bv in range(1<<n):
            dvalues=range(1<<n) if n<=2 else (0,mask,rng.randrange(1<<n))
            for dv in dvalues:
                initial=av|(bv<<n)|(dv<<(2*n))
                expected=av|(bv<<n)|((dv^((av+bv)&mask))<<(2*n))
                assert play_classical(initial,bennett)==expected,(n,av,bv,dv,"Bennett")
                bases+=1
                for outcomes_int in range(1<<(n-1)):
                    outcomes={f"m{i+1}":(outcomes_int>>i)&1 for i in range(n-1)}
                    observed,phase=coherent_phase_branch(initial,measured,outcomes)
                    assert observed==expected,(n,av,bv,dv,outcomes,"wrong output")
                    assert phase==0,(n,av,bv,dv,outcomes,"phase error")
                    branches+=1
    # Each fixed measurement branch is EXACTLY the ideal unitary
    # multiplied by the uniform real amplitude 2^(-(n-1)/2). This also
    # proves equivalence on arbitrary coherent superpositions by linearity.
    return {"basis_states":bases,"outcome_branches":branches,
            "branch_probability":1/(1<<(n-1)),
            "coherent_channel":"EXACT_ALL_BRANCHES_PHASE_ZERO"}

def analyze(n):
    bennett,measured=compose(n)
    proof=verify(n,bennett,measured)
    old=collections.Counter(g for g,*_ in bennett)
    new=collections.Counter(g for g,*_ in measured)
    return {"width":n,"standalone_qubits":4*n-1,"carry_scratch":n-1,
            "bennett_CCX":old["CCX"],"measurement_CCX":new["CCX"],
            "saved_CCX":old["CCX"]-new["CCX"],
            "bennett_CX":old["CX"],"measurement_CX":new["CX"],
            "measurement_HMR":new["HMR"],"conditional_CZ":new["CZ_IF"],
            "conditional_CX":new["CX_IF"],"proof":proof}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
    p.add_argument("--out",type=Path,default=Path("competition/k156/results/measurement_carry.json"))
    p.add_argument("--widths",default="2,3,4,5")
    p.add_argument("--selftest",action="store_true")
    a=p.parse_args()
    for n in (2,3):
        row=analyze(n)
        assert row["saved_CCX"]==2*n-3
    print("K156_SELFTEST PASS all measured branches, arithmetic and coherent phase",flush=True)
    if a.selftest:return
    sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
    ns=sorted(set(map(int,a.widths.split(","))))
    if not ns or min(ns)<2 or max(ns)>5:p.error("exhaustive widths limited to 2..5")
    rows=[]
    for n in ns:
        row=analyze(n);rows.append(row)
        print("K156_CASE",json.dumps(row),flush=True)
    report={"status":"BOUNDED_EXACT_COHERENT_MEASUREMENT_RELEASE_NOT_HELIOS",
            "pinned_sha256":sha,"rows":rows,
            "n14_formula":{"standalone_qubits":55,"carry_scratch":13,
                           "bennett_CCX":50,"measurement_CCX":25,
                           "saved_CCX":25,
                           "note":"Counts are derived from construction, not n14 full phase simulation; 13 carries exceed K151 12 free."},
            "caveats":["No complete 22-bit Helios KMX candidate or official score.",
                       "Conditional CZ/CX Kickmix syntax, legality and score unverified.",
                       "The XOR-into-output adder is not the entire Newton residual multiplier.",
                       "Measurement X plus exact phase repair is safe; raw Z measurement of live carry is not.",
                       "2..5-bit branch checks; arbitrary output values sampled at n>=3."]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print("K156_RESULT",json.dumps({"tested_widths":ns,
      "n14_bennett_CCX":50,"n14_measurement_CCX":25,
      "n14_carry_scratch":13,"full_helios_candidate":False,
      "out":str(a.out)}),flush=True)

if __name__=="__main__":main()
