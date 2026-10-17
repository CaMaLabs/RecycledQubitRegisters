#!/usr/bin/env python3
"""Frozen four-arm N35 active-only vs enable-only relative-phase cached latch test.

Research lead: Chase Lunsford / CaMaLabs.
Inherit the previous COMPLETELY proven phase-exact comparator and modular-add
arithmetic. Only substitute RCCX/inverse for active OR enable temporary control
latch pairs (never both in this four-arm experiment). Check ACTUAL operator
complex output phases, all helper resets, untouched full residue arithmetic,
then compile READ-ONLY IBM Fez native target on CPU. ZERO QPU jobs.
"""
from __future__ import annotations
import argparse,json,os,time,traceback
from pathlib import Path
from datetime import datetime,timezone

from qiskit import QuantumCircuit,QuantumRegister
from qiskit.circuit.library import RCCXGate
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_relative_phase_cached_latch as shared

previous=shared.previous
primitive=shared.primitive
N=35
BITS=6
BASES=(2,8)
VARIANTS=("active_only","enable_only")
REV="qrr-n35-phase-latch-family-ablation-v1-20261017"
OUT=Path("results/ibm_shor35_phase_latch_family_ablation")
BASELINE=shared.BASELINES


def build_variant(base,variant):
    """Identical previous full public multiplier, separate one latch family."""
    if base not in BASES or variant not in VARIANTS:
        raise ValueError("Unpreregistered public base or latch family")
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
        name=f"n35_public_{variant}_base{base}")
    compute=RCCXGate()
    uncompute=compute.inverse()
    phasebit=phase[0]

    def cache_and(ctl0,ctl1,target,relative,reverse=False):
        if relative:
            qc.append(uncompute if reverse else compute,[ctl0,ctl1,target])
        else:
            qc.ccx(ctl0,ctl1,target)

    # Same comparator phase-aware RCCX temporary carries as previous best.
    primitive.predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    active_relative=variant=="active_only"
    enable_relative=variant=="enable_only"

    cache_and(phasebit,valid[0],active[0],active_relative)
    for i in range(BITS):
        cache_and(active[0],work[i],enable[0],enable_relative)
        primitive.modadd(qc,acc,base*(1<<i),N,[enable[0]],
                         wrap[0],carry,scratch)
        cache_and(active[0],work[i],enable[0],enable_relative,reverse=True)

    for old,new in zip(work,acc):
        primitive.controlled_swap(qc,old,new,[active[0]],scratch)
    inv=pow(base,-1,N)
    for i in range(BITS):
        cache_and(active[0],work[i],enable[0],enable_relative)
        primitive.modadd(qc,acc,-inv*(1<<i),N,[enable[0]],
                         wrap[0],carry,scratch)
        cache_and(active[0],work[i],enable[0],enable_relative,reverse=True)
    cache_and(phasebit,valid[0],active[0],active_relative,reverse=True)
    primitive.predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    regs=dict(phase=list(phase),work=list(work),acc=list(acc),
        wrap=list(wrap),valid=list(valid),carry=list(carry),
        scratch=list(scratch),active=list(active),enable=list(enable))
    return qc,regs


def main(base,variant):
    assert base in BASES and variant in VARIANTS
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/f"qrr_n35_{variant}_base{base}.json"
    old=BASELINE[base]
    reference_rccx=old["rccx"]
    replacement=2 if variant=="active_only" else 24
    expected_source=dict(cx=old["cx"],rccx=reference_rccx+replacement,
        x=old["x"],ccx=old["ccx"]-replacement)
    receipt=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        utc=datetime.now(timezone.utc).isoformat(),
        preregistration="docs/QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_PREREG.md",
        N=N,base=base,variant=variant,
        type="full-six-bit-residue single controlled public modular multiplication",
        original_neither_baseline=old,
        original_combined_baseline=(
          dict(cz=8542,depth=19819) if base==2
          else dict(cz=9328,depth=22005)),
        predicted_source_replacement_count=replacement,
        expected_source_gate_distribution=expected_source,
        backend_target="ibm_fez",optimization_level=1,seed_transpiler=8776,
        device_native_cz_cutoff=800,device_native_depth_cutoff=2000,
        full_phase_aware_operator_proof=True,
        input_order_not_injected=True,secret_factors_not_used=True,
        precomputed_multiplicative_orbit_not_used=True,
        actual_qpu_jobs=0,no_quantum_runtime=True,no_paid_runtime=True,
        status="STARTED",success=False)
    def save():path.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        receipt["local_rccx_latch_phase_proof"]=shared.local_latch_unitary_test()
        save()
        print("LOCAL LATCH 8/8 exact complex+1",variant,base,flush=True)
        receipt["unchanged_comparator_phase_proof"]=previous.exhaustive_comparator_phase_proof()
        save()
        print("COMPARATOR 42672/42672 exact complex+1",variant,base,flush=True)
        receipt["unchanged_modadd_phase_proof"]=previous.exhaustive_modadd_phases(previous.source_constants())
        save()
        print("PUBLIC MODADD 1584/1584 exact complex+1",variant,base,flush=True)

        qc,regs=build_variant(base,variant)
        whole=previous.exhaustive_full_multiplier_phases(qc,regs,base)
        receipt["full_multiplier_phase_proof"]=whole
        receipt["source_logical_qubits"]=qc.num_qubits
        actual=whole["quantum_source_gate_counts"]
        if actual!=expected_source or qc.num_qubits!=32:
            raise AssertionError(json.dumps(dict(
                intervention_not_exercised_or_changed_arithmetic=True,
                expected=expected_source,actual=actual,
                application_logical_qubits=qc.num_qubits)))
        receipt["actual_latch_replacement_count"]=replacement
        receipt["status"]="ALL_COMPLEX_GATE_PROOFS_PASS"
        save()
        print("FULL SOURCE MULTIPLIER PHASE+1 128/128 ALL 25 HELPER CLEAN",
              variant,base,"source",actual,flush=True)

        # Read target; do not construct/run Qiskit Runtime primitives.
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<qc.num_qubits:
            raise RuntimeError("Backend is not sufficiently wide real target")
        receipt["backend_device_qubits"]=backend.num_qubits
        receipt["status"]="COMPILING_NATIVE_CPU_ONLY"
        save()
        pm=generate_preset_pass_manager(backend=backend,
            optimization_level=1,seed_transpiler=8776)
        t0=time.perf_counter()
        native=pm.run(qc)
        sec=time.perf_counter()-t0
        ops={str(k):int(v) for k,v in native.count_ops().items()}
        cz=ops.get("cz",0);depth=native.depth()
        eng=cz<old["cz"] and depth<old["depth"]
        device=cz<=800 and depth<=2000
        receipt.update(status="COMPILE_SUCCESS",success=True,
            compiled_native_cz=cz,compiled_native_depth=depth,
            compiled_native_ops=ops,compiled_device_width=native.num_qubits,
            compiled_total_gates=native.size(),compile_seconds=sec,
            cz_delta_from_neither=cz-old["cz"],
            depth_delta_from_neither=depth-old["depth"],
            engineering_arm_both_metrics_improve=bool(eng),
            hardware_gate_pass=bool(device))
        save()
        print("N35 CACHED-LATCH FAMILY CPU FEZ",
              variant,base,"CZ",cz,"DEPTH",depth,
              "ENGINEERING",eng,"DEVICE",device,"NO QPU",flush=True)
        return 0
    except Exception as e:
        receipt.update(status="FAIL",success=False,
            failure_class=type(e).__name__,
            failure_message=str(e)[:1800],
            traceback=traceback.format_exc()[-2500:],
            actual_qpu_jobs=0,no_quantum_runtime=True)
        save()
        print("N35 CACHED-LATCH FAMILY FAIL",variant,base,
              type(e).__name__,str(e)[:500],traceback.format_exc()[-1200:],
              "NO QPU",flush=True)
        return 1


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,required=True,choices=BASES)
    p.add_argument("--variant",required=True,choices=VARIANTS)
    a=p.parse_args()
    raise SystemExit(main(a.base,a.variant))
