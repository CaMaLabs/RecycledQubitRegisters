#!/usr/bin/env python3
"""N35 public cached control latches use phase-correct RCCX compute/uncompute.

Research lead: Chase Lunsford / CaMaLabs.
Keep prior best comparator RCCX, public six-bit full-residue arithmetic,
modular-add and 32-qubit controlled multiplier exactly. Change ONLY active and
enable cached control pairs from CCX/CCX to RCCX/RCCX.inverse().
Actual emitted quantum Operator matrices and complex phases are verified on
8 local latch + 42672 comparator + 1584 modadd + 128 complete cases per base.
IBM Fez hardware TARGET is read-only for CPU compilation. ZERO QPU jobs.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import RCCXGate
from qiskit.quantum_info import Operator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

# This import patches the ORIGINAL primitive.predicate only, for phase-exact
# comparator carry RCCX/adjoint, and retains old prefix-carry modular addition.
import qrr_n35_relative_phase_ripple_carry as previous
import qrr_n35_single_modmul_ripple_toffoli as primitive

N=35
BITS=6
REV="qrr-n35-relative-phase-cached-active-enable-v1-20261017"
ROOT=Path("results/ibm_shor35_phase_cached_latch")
BASELINES={2:dict(cz=9263,depth=21772,logical=32,rccx=596,ccx=160,cx=1033,x=28),
           8:dict(cz=9426,depth=21933,logical=32,rccx=616,ccx=162,cx=1077,x=28)}
EPS=1e-8


def check_inverse_operator():
    forward=np.asarray(Operator(RCCXGate()).data,dtype=complex)
    backward=np.asarray(Operator(RCCXGate().inverse()).data,dtype=complex)
    if not np.allclose(backward@forward,np.eye(8),atol=EPS):
        raise AssertionError("RCCX and actual Qiskit inverse not unitary inverses")
    return dict(actual_inverse_gate_name=RCCXGate().inverse().name,
        operator_product_is_identity=True)


def local_latch_unitary_test():
    """Test one complete RCCX, semantic use of cached control, inverse RCCX."""
    details=check_inverse_operator()
    ctrl=QuantumRegister(2,"ctrl")
    latch=QuantumRegister(1,"latch")
    probe=QuantumRegister(1,"probe")
    qc=QuantumCircuit(ctrl,latch,probe)
    qc.append(RCCXGate(),[ctrl[0],ctrl[1],latch[0]])
    qc.cx(latch[0],probe[0])
    qc.append(RCCXGate().inverse(),[ctrl[0],ctrl[1],latch[0]])
    ix,inst,count=previous.actual_complex_instructions(qc)
    assert count.get('rccx',0)==2 and count.get('cx',0)==1,(count,details)
    tested=0
    cp=[ix[q] for q in ctrl]
    lp=ix[latch[0]]
    pp=ix[probe[0]]
    for c in range(4):
        for oldprobe in (0,1):
            init=((c&1)<<cp[0])|(((c>>1)&1)<<cp[1])|(oldprobe<<pp)
            out,phase=previous.evolve_basis(inst,init)
            expected_probe=oldprobe^int(c==3)
            if ((out>>pp)&1)!=expected_probe or ((out>>lp)&1)!=0:
                raise AssertionError(f"Cached latch local bits wrong c={c} probe={oldprobe}")
            if any(((out>>p)&1)!=((c>>i)&1) for i,p in enumerate(cp)):
                raise AssertionError("Cached latch local controls changed")
            previous.check_exact_phase(phase,f"cached latch c={c} probe={oldprobe}")
            tested+=1
    assert tested==8
    return dict(pass_all=True,direct_actual_operator_cases=tested,
        initial_latch_zero=True, final_latch_zero=True,
        controls_preserved=True,semantic_controlled_probe_exact=True,
        output_complex_phase_exactly_plus_one=True,
        source_operation_counts=count,**details)


def build_public_multiplier(base):
    """Original cached control modular multiply, with ONLY temporary RCCX latches."""
    if base not in BASELINES:raise ValueError("Unfrozen base")
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
        name=f"n35_relative_cached_latches_base{base}")
    phasebit=phase[0]
    compute=RCCXGate()
    reverse=compute.inverse()
    # Unchanged publicly known valid threshold; comparator RCCX carry source
    # is supplied by the verified previous module import.
    primitive.predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    # NEW COMPONENT: active latch relative-phase compute, exact inverse later.
    qc.append(compute,[phasebit,valid[0],active[0]])
    for i in range(BITS):
        # NEW COMPONENT: temporary per-input source enable latch.
        qc.append(compute,[active[0],work[i],enable[0]])
        # Same verified modulo35 add, all controls unchanged during arithmetic.
        primitive.modadd(qc,acc,base*(1<<i),N,[enable[0]],
                         wrap[0],carry,scratch)
        qc.append(reverse,[active[0],work[i],enable[0]])
    # Semantic controlled swaps NEVER use relative-phase CCX for target.
    for a,b in zip(work,acc):
        primitive.controlled_swap(qc,a,b,[active[0]],scratch)
    inv=pow(base,-1,N)
    for i in range(BITS):
        qc.append(compute,[active[0],work[i],enable[0]])
        primitive.modadd(qc,acc,-inv*(1<<i),N,[enable[0]],
                         wrap[0],carry,scratch)
        qc.append(reverse,[active[0],work[i],enable[0]])
    qc.append(reverse,[phasebit,valid[0],active[0]])
    primitive.predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    return qc,dict(phase=list(phase),work=list(work),acc=list(acc),
        wrap=list(wrap),valid=list(valid),carry=list(carry),
        scratch=list(scratch),active=list(active),enable=list(enable))


def main(base):
    assert base in (2,8)
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f"qrr_n35_phase_cached_latch_base{base}.json"
    receipt=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        preregistered_document="docs/QRR_N35_RELATIVE_PHASE_CACHED_LATCH_PREREG.md",
        utc=datetime.now(timezone.utc).isoformat(),
        base=base,N=N,
        kind="one honest public six-bit-residue controlled modular multiplier",
        previous_frozen_baseline=BASELINES[base],
        intervention="only 26 cached active and enable latch standard CCX -> RCCX / actual inverse",
        backend_target="ibm_fez",transpiler_optimization=1,transpiler_seed=8776,
        frozen_native_cz_cutoff=800,frozen_native_depth_cutoff=2000,
        full_phase_exact_gate_proofs_required=True,
        factors_not_used=True,order_not_injected=True,orbit_not_compiled=True,
        qpu_jobs_submitted=0,quantum_runtime_used=False,paid_runtime_used=False,
        status="STARTED",success=False)
    def save():path.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        receipt["local_latch_complex_proof"]=local_latch_unitary_test()
        save()
        print("PHASE-EXACT CACHED LATCH PROOF",base,
              receipt["local_latch_complex_proof"]["direct_actual_operator_cases"],
              "all +1 phase, all scratch clean",flush=True)
        receipt["comparator_complex_proof"]=previous.exhaustive_comparator_phase_proof()
        save()
        print("UNCHANGED RIPPLE COMPARATOR PHASE-EXACT OPERATOR GATES",base,
             receipt["comparator_complex_proof"]["actual_gate_comparator_cases"],
             "phase +1",flush=True)
        receipt["modadd_complex_proof"]=previous.exhaustive_modadd_phases(previous.source_constants())
        save()
        print("UNCHANGED 16 PUBLIC MODADD PHASE-EXACT OPERATOR GATES",base,
             receipt["modadd_complex_proof"]["source_gate_cases"],flush=True)
        qc,regs=build_public_multiplier(base)
        receipt["full_multiplier_complex_proof"]=previous.exhaustive_full_multiplier_phases(qc,regs,base)
        receipt["source_logical_qubits"]=qc.num_qubits
        actual=receipt["full_multiplier_complex_proof"]["quantum_source_gate_counts"]
        old=BASELINES[base]
        expected=dict(rccx=old["rccx"]+26,ccx=old["ccx"]-26,
                      cx=old["cx"],x=old["x"])
        if actual!=expected:
            raise AssertionError("Cached RCCX intervention not exact or not exercised: "+
                                 json.dumps(dict(actual=actual,expected=expected)))
        receipt["verified_source_latch_replacements"]=26
        receipt["status"]="ALL_COMPLEX_GATE_PROOFS_PASS"
        save()
        print("FULL MULTIPLIER EXACT PHASE",base,"128/128, 25 CLEAN",
              "changed latch RCCX 26 source",actual,flush=True)
        # IBM target READ ONLY. No quantum primitive construction or QPU job.
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<qc.num_qubits:
            raise RuntimeError("Backend is not a suitably wide physical target")
        receipt["backend_qubits"]=backend.num_qubits
        receipt["status"]="COMPILING_NATIVE_CPU_ONLY"
        save()
        pm=generate_preset_pass_manager(backend=backend,
            optimization_level=1,seed_transpiler=8776)
        t0=time.perf_counter()
        compiled=pm.run(qc)
        dur=time.perf_counter()-t0
        ops={str(k):int(v) for k,v in compiled.count_ops().items()}
        cz=ops.get("cz",0)
        depth=compiled.depth()
        eng=cz<old["cz"] and depth<old["depth"]
        phys=cz<=800 and depth<=2000
        receipt.update(status="COMPILE_SUCCESS",success=True,
            native_cz=cz,native_depth=depth,native_size=compiled.size(),
            compiled_device_width=compiled.num_qubits,
            compiled_native_ops=ops,compile_seconds=dur,
            native_cz_delta=cz-old["cz"],native_depth_delta=depth-old["depth"],
            native_cz_change_pct=100*(cz-old["cz"])/old["cz"],
            native_depth_change_pct=100*(depth-old["depth"])/old["depth"],
            engineering_gate_pass=bool(eng),
            hardware_feasibility_gate_pass=bool(phys))
        save()
        print("N35 RCCX CACHED LATCH CPU NATIVE",base,
            "CZ",cz,"DEPTH",depth,
            "ENGINEERING",eng,"HARDWARE",phys,"ZERO QPU",flush=True)
        return 0
    except Exception as e:
        receipt.update(status="FAIL",success=False,
            failure_class=type(e).__name__,
            failure_message=str(e)[:1800],
            failure_trace=traceback.format_exc()[-2800:],
            qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print("N35 CACHED LATCH FAILED",base,type(e).__name__,
              str(e)[:700],traceback.format_exc()[-1200:],"ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",required=True,type=int,choices=[2,8])
    raise SystemExit(main(parser.parse_args().base))
