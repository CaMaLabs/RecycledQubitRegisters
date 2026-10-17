#!/usr/bin/env python3
"""Public-only cached-enable control experiment: one N=35 controlled modular multiply.

Rigor: reuse the actual verified primitive ripple/Toffoli arithmetic functions;
change ONLY how repeated external controls are materialized. Exhaustively
interpret all X/CX/CCX instructions across 128 input control/work basis states
and require every ancillary register INCLUDING the new latches clean. Read
IBM Fez native TARGET for Qiskit compilation; ZERO QPU jobs/Runtime primitives.

Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import argparse,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_single_modmul_ripple_toffoli as reference

N=35
BITS=6
BASES=(2,8)
REV="qrr-n35-cached-enable-primitive-modmul-v1-20261016"
OUT=Path("results/ibm_shor35_ripple_cached_controls")
BASELINE={2:dict(primitive=1964,logical=30,cz=27929,depth=59947),
          8:dict(primitive=2062,logical=30,cz=29822,depth=63922)}

def build(base):
    assert base in BASES
    phase=QuantumRegister(1,"phase")
    work=QuantumRegister(BITS,"work")
    acc=QuantumRegister(BITS,"acc")
    wrap=QuantumRegister(1,"wrap")
    valid=QuantumRegister(1,"valid")
    carry=QuantumRegister(BITS,"carry")
    scratch=QuantumRegister(BITS+3,"scratch")
    active=QuantumRegister(1,"active")
    enable=QuantumRegister(1,"enable")
    qc=QuantumCircuit(phase,work,acc,wrap,valid,carry,scratch,active,enable,
        name=f"n35_public_latched_ctrlmodmul_base{base}")
    p=phase[0]
    # Base and public modulus alone determine the full-residue unitary.
    # Predicate implementation is UNCHANGED from reference gate-proved kernel.
    reference.predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    # Only optimization under test: compute and reuse a clean `active`
    # in place of repeatedly controlling on phase AND validity.
    qc.ccx(p,valid[0],active[0])
    for i in range(BITS):
        qc.ccx(active[0],work[i],enable[0])
        reference.modadd(qc,acc,base*(1<<i),N,[enable[0]],
                         wrap[0],carry,scratch)
        qc.ccx(active[0],work[i],enable[0])
    for old,new in zip(work,acc):
        reference.controlled_swap(qc,old,new,[active[0]],scratch)
    inv=pow(base,-1,N)
    for i in range(BITS):
        qc.ccx(active[0],work[i],enable[0])
        reference.modadd(qc,acc,-inv*(1<<i),N,[enable[0]],
                         wrap[0],carry,scratch)
        qc.ccx(active[0],work[i],enable[0])
    qc.ccx(p,valid[0],active[0])
    reference.predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    regs=dict(phase=list(phase),work=list(work),acc=list(acc),
        wrap=list(wrap),valid=list(valid),carry=list(carry),
        scratch=list(scratch),active=list(active),enable=list(enable))
    return qc,regs


def exhaustive_actual_gate_proof(qc,regs,base):
    index={bit:i for i,bit in enumerate(qc.qubits)}
    gate_counts={}
    instructions=[]
    for instr in qc.data:
        name=instr.operation.name
        assert name in ("x","cx","ccx"),("A nonprimitive gate",name)
        gate_counts[name]=gate_counts.get(name,0)+1
        vals=[index[b] for b in instr.qubits]
        assert len(vals)=={"x":1,"cx":2,"ccx":3}[name]
        assert len(set(vals))==len(vals)
        instructions.append((tuple(vals[:-1]),vals[-1]))
    p=index[regs["phase"][0]]
    work=[index[x] for x in regs["work"]]
    aux=[index[x] for category in ("acc","wrap","valid","carry","scratch","active","enable")
          for x in regs[category]]
    assert len(aux)==25 and len(set(aux))==len(aux) and qc.num_qubits==32
    assert set(aux).isdisjoint({p,*work})
    cases=0
    for control in (0,1):
        for y in range(64):
            state=control<<p
            for j,pos in enumerate(work):
                state|=((y>>j)&1)<<pos
            for src,dst in instructions:
                if all((state>>j)&1 for j in src):
                    state^=1<<dst
            result=sum(((state>>pos)&1)<<i for i,pos in enumerate(work))
            expected=(base*y)%N if control and y<N else y
            dirty=[j for j in aux if (state>>j)&1]
            if result!=expected or ((state>>p)&1)!=control or dirty:
                raise AssertionError(json.dumps(dict(base=base,control=control,y=y,
                    expected=expected,actual=result,dirty_aux=dirty,
                    control_preserved=((state>>p)&1)==control)))
            cases+=1
    return dict(pass_all=True,actual_emitted_instruction_interpreter=True,
        exhaustive_control_residue_inputs=cases,all_aux_25_clean=True,
        full_work_input_values=64,
        control_off_identity=True,invalid_y_identity=True,
        source_primitive_gate_counts=gate_counts,
        primitive_gate_count=len(instructions))


def main(base):
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/f"qrr_n35_cached_enable_single_mul_base{base}.json"
    record=dict(revision=REV,lead="Chase Lunsford / CaMaLabs",
        date_utc=datetime.now(timezone.utc).isoformat(),
        prereg="docs/QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_PREREG.md",
        base=base,N=N,kind="one full-residue public controlled modular multiplier; NOT QPE",
        baseline=BASELINE[base],
        change="precompute/reuse active=phase AND valid and per-source enable=active AND workbit",
        algorithm_reference="hardware/qrr_n35_single_modmul_ripple_toffoli.py",
        qpu_jobs=0,no_runtime_submission=True,
        no_order_or_orbit_used=True,
        target_backend="ibm_fez",optimization_level=1,seed_transpiler=8776,
        frozen_native_cz_limit=800,frozen_native_depth_limit=2000,
        status="STARTED",success=False)
    def save():path.write_text(json.dumps(record,indent=2,default=str)+"\n")
    save()
    try:
        circuit,registers=build(base)
        proof=exhaustive_actual_gate_proof(circuit,registers,base)
        assert proof["pass_all"] and proof["exhaustive_control_residue_inputs"]==128
        record.update(status="SEMANTICS_PROVED",proof=proof,
            source_logical_qubits=circuit.num_qubits,
            source_depth=circuit.depth(),source_size=circuit.size())
        save()
        print("GATE LEVEL SEMANTICS PASS",base,
              "128/128, all 25 helpers clean, primitive",circuit.size(),
              "logical",circuit.num_qubits,flush=True)
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        assert not getattr(backend,"simulator",False)
        assert backend.num_qubits>=circuit.num_qubits
        record["backend_qubits"]=backend.num_qubits
        record["status"]="COMPILING"
        save()
        pm=generate_preset_pass_manager(backend=backend,
            optimization_level=1,seed_transpiler=8776)
        start=time.perf_counter()
        compiled=pm.run(circuit)
        duration=time.perf_counter()-start
        ops={str(k):int(v) for k,v in compiled.count_ops().items()}
        cz=int(ops.get("cz",0));depth=int(compiled.depth())
        gates_better=cz<BASELINE[base]["cz"] and depth<BASELINE[base]["depth"]
        feasible=cz<=800 and depth<=2000
        record.update(status="COMPILE_SUCCESS",success=True,
            compiled_device_width=int(compiled.num_qubits),
            compiled_native_ops=ops,native_cz=cz,native_depth=depth,
            native_size=int(compiled.size()),compile_seconds=duration,
            primitive_optimization_pass=bool(gates_better),
            frozen_hardware_feasibility_pass=bool(feasible),
            cz_delta_from_frozen_baseline=cz-BASELINE[base]["cz"],
            depth_delta_from_frozen_baseline=depth-BASELINE[base]["depth"])
        save()
        print("N35 CACHED_ENABLE BASE",base,"CZ",cz,"DEPTH",depth,
              "ENGINEERING_GATE",gates_better,"HARDWARE_GATE",feasible,
              "ZERO_QPU",flush=True)
        return 0
    except Exception as e:
        record.update(status="FAIL",success=False,
            error_class=type(e).__name__,error=str(e)[:900],qpu_jobs=0)
        save()
        print("ZERO_QPU ERROR",type(e).__name__,str(e)[:450],flush=True)
        return 1

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(ap.parse_args().base))
