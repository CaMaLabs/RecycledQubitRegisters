#!/usr/bin/env python3
"""A39: compare MCX synthesis/ancilla strategies for exact N143 multiplier.

Identical A37 controlled permutation with two decompositions: baseline
no-ancilla and v-chain with clean scratch. The latter is a reversible
implementation change, NOT structured modular arithmetic yet.
Only compile results count; no claims about physical hardware or full Shor.
"""
from __future__ import annotations
import argparse, json, sys, time, traceback
from pathlib import Path
from qiskit import QuantumCircuit, transpile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware"))
import qrr_a37_n143_gate_audit_optimizer as a37

def lower_with_clean_ancilla(source):
    # A37 has nine qubits, 0=phase, 1..8=work. Add six clean scratch
    # for the 8-controlled MCX. Qiskit's v-chain uncomputes scratch.
    nwork=source.num_qubits
    scratch=6
    target=QuantumCircuit(nwork+scratch)
    for inst in source.data:
        name=inst.operation.name
        idx=[source.find_bit(q).index for q in inst.qubits]
        if name=="x":
            target.x(idx[0])
        elif name=="mcx":
            controls=idx[:-1]
            required=max(0,len(controls)-2)
            if required>scratch:
                raise AssertionError("Insufficient clean scratch")
            target.mcx(controls,idx[-1],
                       ancilla_qubits=list(range(nwork,nwork+required)),
                       mode="v-chain")
        else:
            raise AssertionError("Unexpected source gate "+name)
    return target

def counts(q):
    return {str(k):int(v) for k,v in q.count_ops().items()}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bases",nargs="+",type=int,default=[2,8])
    p.add_argument("--optimization-level",type=int,choices=[0,1,2,3],default=0)
    p.add_argument("--output",default="results/a39_mcx_synthesis_ancilla.json")
    a=p.parse_args()
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    report={
      "experiment":"A39_N143_CLEAN_ANCILLA_MCX_SYNTHESIS",
      "status":"IN_PROGRESS","qpu_jobs":0,"basis_gates":["u","cx"],
      "notes":"Both circuits implement A37 exact permutation. v-chain uses SIX additional clean ancillas; no whole-circuit dynamic phase-estimation or fault-tolerant cost.",
      "structured_modular_multiplier_implemented":False,
      "quaspy_n143_connected":False,
      "rows":[]
    }
    def save():out.write_text(json.dumps(report,indent=2)+"\n")
    save()
    try:
        for base in a.bases:
            t0=time.perf_counter()
            src=a37.optimized_multiply(base)
            assert a37.verify(src,base)==512
            variants={"baseline":src,"v_chain_clean":lower_with_clean_ancilla(src)}
            values={}
            for name,circuit in variants.items():
                start=time.perf_counter()
                compiled=transpile(circuit,basis_gates=["u","cx"],
                    optimization_level=a.optimization_level,seed_transpiler=20261030)
                ops=counts(compiled)
                assert set(ops).issubset({"u","cx"}),ops
                values[name]=dict(logical_qubits=circuit.num_qubits,
                    source_counts=counts(circuit),decomposed_counts=ops,
                    depth=compiled.depth(),
                    compile_seconds=round(time.perf_counter()-start,3))
                print(base,name,ops,"depth",compiled.depth(),flush=True)
            b=values["baseline"];v=values["v_chain_clean"]
            bcx=b["decomposed_counts"].get("cx",0);vcx=v["decomposed_counts"].get("cx",0)
            row={"base":base,"basis_states_verified_on_original":512,
                 "baseline":b,"clean_ancilla_v_chain":v,
                 "cx_difference":bcx-vcx,
                 "cx_reduction_fraction":(bcx-vcx)/bcx if bcx else None,
                 "additional_clean_ancillas":6,
                 "elapsed_seconds":round(time.perf_counter()-t0,3)}
            report["rows"].append(row);save()
        report["status"]="PASS_COMPARABLE_DECOMPOSITION_RESOURCE_LEDGER"
    except Exception as exc:
        report["status"]="FAIL_OR_UNSUPPORTED_NO_OPTIMIZATION_CLAIM"
        report["error"]=repr(exc)
        report["traceback"]=traceback.format_exc()[-3000:]
    save()
    print(json.dumps({k:v for k,v in report.items() if k not in ("rows","traceback")},indent=2))
    print("SAVED",out)
    return 0 if report["status"].startswith("PASS") else 1
if __name__=="__main__":
    raise SystemExit(main())
