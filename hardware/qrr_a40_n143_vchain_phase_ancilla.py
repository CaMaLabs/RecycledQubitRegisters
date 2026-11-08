#!/usr/bin/env python3
"""A40: validate N143 v-chain MCX semantics before QPE integration.

Local statevector checks verify the 8-control gate's full complex output
amplitude and clean ancillas. Whole-multiplier exact basis-map is established
by A37/A36 construction; optional Aer MPS spot checks test actual A39 circuit.
No QPU, no factoring claim.
"""
import argparse,json,sys,time,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import MCXVChain

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a37_n143_gate_audit_optimizer as a37

def vchain_source(base):
    src=a37.optimized_multiply(base)
    out=QuantumCircuit(15)
    for inst in src.data:
        inds=[src.find_bit(q).index for q in inst.qubits]
        name=inst.operation.name
        if name=="x":out.x(inds[0])
        elif name=="mcx":
            nc=len(inds)-1
            assert nc==8
            gate=MCXVChain(nc,dirty_ancillas=False,relative_phase=False,action_only=False)
            out.append(gate,inds+list(range(9,15)))
        else:raise AssertionError(name)
    return out

def local_phase_and_ancilla_audit():
    gate=MCXVChain(8,dirty_ancillas=False,relative_phase=False,action_only=False)
    template=QuantumCircuit(15)
    template.append(gate,list(range(15)))
    # Test every one of 2**8 control strings, target=0 and 1.
    # Each test has an independent basis state with all scratch zero.
    failures=[]
    tested=0
    max_dev=0.0
    for ctrl in range(256):
        for target in (0,1):
            initial=ctrl+(target<<8)
            state=Statevector.from_int(initial,2**15).evolve(template)
            expected=initial ^ ((1<<8) if ctrl==255 else 0)
            amp=complex(state.data[expected])
            deviation=float(max(abs(amp-1),np.linalg.norm(state.data)**2-abs(amp)**2))
            max_dev=max(max_dev,deviation)
            if deviation>1e-9:
                failures.append({"ctrl":ctrl,"target":target,"amplitude":[amp.real,amp.imag],"deviation":deviation})
                if len(failures)>5:break
            tested+=1
        if failures:break
    if failures:raise AssertionError("Local VChain semantics failure: "+repr(failures))
    return {"tested_complex_basis_inputs":tested,"scratch_returned_zero":True,
            "relative_phase_none":True,"maximum_amplitude_error":max_dev}

def full_spot(base,work,control,shots):
    from qiskit_aer import AerSimulator
    from qiskit import transpile
    qc=vchain_source(base)
    if control:qc.x(0)
    for j in range(8):
        if work>>j&1:qc.x(j+1)
    qc.measure_all()
    sim=AerSimulator(method="matrix_product_state",max_parallel_threads=4)
    compiled=transpile(qc,sim,optimization_level=0,seed_transpiler=20261030)
    result=sim.run(compiled,shots=shots,seed_simulator=20261030).result()
    counts=result.get_counts()
    expected_work=(base*work%143 if work<143 else work) if control else work
    expected=control+(expected_work<<1)
    assert counts=={format(expected,"015b"):shots},(counts,expected)
    return {"control":control,"input":work,"expected_work":expected_work,
            "counts":counts,"pass":True,"depth":compiled.depth()}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bases",type=int,nargs="+",default=[2,8])
    p.add_argument("--spot-check",action="store_true")
    p.add_argument("--output",default="results/a40_vchain_ancilla_phase_audit.json")
    a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    report={"experiment":"A40_N143_VCHAIN_PHASE_AND_CLEAN_ANCILLA",
            "status":"IN_PROGRESS","qpu_jobs":0,"full_qpe_integrated":False,
            "quaspy_n143_integrated":False,"rows":[]}
    def save():out.write_text(json.dumps(report,indent=2)+"\n")
    save()
    t=time.perf_counter()
    try:
        report["local_vchain"]=local_phase_and_ancilla_audit()
        print("LOCAL VCHAIN VERIFIED:",report["local_vchain"],flush=True)
        for base in a.bases:
            if math.gcd(base,143)!=1:raise ValueError("Non-coprime base")
            assert a37.verify(a37.optimized_multiply(base),base)==512
            row={"base":base,"original_basis_checked":512,"local_phase_gate_verified":True,
                 "full_vchain_gate_level_spots":[]}
            if a.spot_check:
                for control,work in ((0,1),(1,1)):
                    row["full_vchain_gate_level_spots"].append(full_spot(base,work,control,1))
            report["rows"].append(row);save()
        report["status"]="PASS_LOCAL_VCHAIN_PHASE_AND_ANCILLA_AUDIT"
        if a.spot_check:report["status"]="PASS_LOCAL_AND_FULL_CIRCUIT_SPOT_CHECKS"
    except Exception as exc:
        report["status"]="FAIL_NOT_VALIDATED"
        report["error"]=repr(exc)
        save()
        raise
    report["wall_seconds"]=round(time.perf_counter()-t,2)
    save()
    print(json.dumps(report,indent=2),flush=True)
    return 0
if __name__=="__main__":raise SystemExit(main())
