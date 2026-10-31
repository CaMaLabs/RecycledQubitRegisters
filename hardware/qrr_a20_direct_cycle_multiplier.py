#!/usr/bin/env python3
"""A20: genuinely different 6-bit controlled permutation using adjacent-state
transpositions. Source-level exact 128-basis proof before optional native Fez
CPU transpilation. Diagnostic candidate only, NOT a replacement by default.
No QPU jobs. Never alters Quaspy or established arithmetic.
"""
import argparse,json,math,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

N=35
def cycles(power):
    mapping={y:(power*y)%N for y in range(N)}
    seen=set();out=[]
    for start in range(N):
        if start in seen:continue
        cycle=[];x=start
        while x not in seen:
            seen.add(x);cycle.append(x);x=mapping[x]
        assert x==start
        if len(cycle)>1:out.append(cycle)
    return out

def path(a,b):
    vertices=[a]
    for i in range(6):
        if (a^b)&(1<<i):
            a^=1<<i;vertices.append(a)
    assert a==b
    return vertices

def circuit(power):
    qr=QuantumRegister(1,"control")
    wr=QuantumRegister(6,"work")
    qc=QuantumCircuit(qr,wr)
    swap_edges=0
    def adjacent(a,b):
        nonlocal swap_edges
        bit=(a^b).bit_length()-1
        assert a^b==1<<bit
        # Set the 5 non-target work controls to match the common state.
        for j in range(6):
            if j!=bit and not ((a>>j)&1):qc.x(wr[j])
        qc.mcx([qr[0]]+[wr[j] for j in range(6) if j!=bit],wr[bit])
        for j in range(6):
            if j!=bit and not ((a>>j)&1):qc.x(wr[j])
        swap_edges+=1
    def transpose(a,b):
        p=path(a,b)
        for i in range(len(p)-1):adjacent(p[i],p[i+1])
        for i in range(len(p)-3,-1,-1):adjacent(p[i],p[i+1])
    for cy in cycles(power):
        pivot=cy[0]
        # Apply (pivot,cy[1]) then (pivot,cy[2]) etc -> desired forward cycle.
        for vertex in cy[1:]:transpose(pivot,vertex)
    return qc,swap_edges

def verify(qc,power):
    """Exact computational-basis reversible action; only x/mcx have phase +1."""
    assert set(qc.count_ops()).issubset({"x","mcx"})
    for control in (0,1):
        for y in range(64):
            bits=[control]+[(y>>i)&1 for i in range(6)]
            for ins in qc.data:
                indices=[qc.find_bit(q).index for q in ins.qubits]
                if ins.operation.name=="x":bits[indices[0]]^=1
                elif ins.operation.name=="mcx":
                    if all(bits[i] for i in indices[:-1]):bits[indices[-1]]^=1
                else:raise AssertionError("non-permutation gate")
            want=(power*y)%N if control and y<N else y
            got=sum(bits[i+1]<<i for i in range(6))
            assert bits[0]==control and got==want,(power,control,y,got,want)
    return 128

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--native",action="store_true",help="read-only Fez CPU compile, 2 seeds per power, no QPU")
    p.add_argument("--output",default="results/qrr_a20_transposition_multiplier.json")
    a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    report={"status":"STARTED","candidate":"direct Gray-path basis transpositions, no ancilla",
      "qpu_jobs":0,"powers":[8,29],"rows":[]}
    def save():out.write_text(json.dumps(report,indent=2)+"\n")
    try:
        compiled={}
        for power in (8,29):
            qc,edges=circuit(power)
            exact=verify(qc,power)
            row={"power":power,"cases":exact,"transposition_edges":edges,
                 "cycles":[len(x) for x in cycles(power)],
                 "source_gates":{str(k):int(v) for k,v in qc.count_ops().items()},
                 "source_qubits":qc.num_qubits}
            report["rows"].append(row)
            compiled[power]=qc;save()
            print("A20 EXACT",power,exact,"edges",edges,"mcx",qc.count_ops().get("mcx",0),flush=True)
        report["status"]="SOURCE_EXACT_PASS";save()
        if a.native:
            from qiskit_ibm_runtime import QiskitRuntimeService
            backend=QiskitRuntimeService().backend("ibm_fez")
            for row in report["rows"]:
                row["native"]=[]
                for seed in (509,1223):
                    pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed)
                    isa=pm.run(compiled[row["power"]])
                    row["native"].append({"seed":seed,"cz":int(isa.count_ops().get("cz",0)),"depth":isa.depth()})
                    save()
                    print("A20 NATIVE",row["power"],seed,row["native"][-1],flush=True)
            report["status"]="NATIVE_DONE";save()
        print(json.dumps({"status":report["status"],"qpu_jobs":0,"rows":report["rows"]},indent=2))
    except Exception:
        report["status"]="FAIL";report["traceback"]=traceback.format_exc();save();raise
if __name__=="__main__":main()
