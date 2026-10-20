#!/usr/bin/env python3
"""Public constant-local static 2-qubit-gate-cost sign selector, N35 zero QPU.

Originating research: Chase Lunsford / CaMaLabs.
Frozen BEFORE compilation: for each k=1..34 synthesize phase-aware POSITIVE
and SIGNED/UNDERFLOW clean modulo35 add; compare SOURCE proxy
    CX + 6*CCX + 3*RCCX
and use signed iff strictly cheaper. Exactly the SAME public 34-entry table
for both public multiplier bases. Prove complex +1 quantum phase for BOTH
adder versions across all 34*2*99 basis cases and for the complete two old/new
32-qubit full-residue quantum source multipliers BEFORE any IBM backend read.
Then matched 8 predeclared Qiskit CPU Fez target transpiler seeds per base,
ALL original outcomes preserved; absolutely no IBM QPU jobs/runtime.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_signed_constant_correction_multiseed as signed

old=signed.old
dm=signed.dm
previous=signed.previous
primitive=signed.primitive
best=signed.best

N=35
BITS=6
BASES=(2,8)
SEEDS=(11,37,101,409,8776,12011,20261,45673)
REV="qrr-n35-static-source-gate-sign-selector-v1-20261019"
ROOT=Path("results/ibm_shor35_static_gate_sign_selector")
HISTORICAL={
    2:dict(cz=7887,depth=18221,
        source=dict(cx=303,rccx=596,x=1738,ccx=160)),
    8:dict(cz=7802,depth=18449,
        source=dict(cx=311,rccx=616,x=1828,ccx=162))
}
POSITIVE_MODADD=signed.ORIGINAL_BEST_MODADD
SELECTION={}
SIGNED_CALLS=0
POSITIVE_CALLS=0


def bootstrap_original_best():
    """Return ALL dynamic arithmetic dependencies to original robust one-bit."""
    old.ensure_strong_demorgan_baseline()
    best.constant_add_from_prefix_carry=old.one_bit_bypass_constant_add
    best.optimized_modadd=POSITIVE_MODADD
    primitive.modadd=POSITIVE_MODADD


def signed_all_k_modadd(qc,target,k,modulus,controls,flag,carry,chain):
    """Exact underflow branch for EVERY public k in 1..34, not just k>17.

    Public d=N-k. Conditioned on original target x<d, subtract d; if underflow
    add N, then clean flag using final output >=k. All additions inherit
    unchanged public one-bit prefix-carry bypass and phase-correct De Morgan.
    """
    k=int(k)%int(modulus)
    if k==0:return
    d=int(modulus)-k
    controls=list(controls)
    best.public_threshold_predicate(qc,target,d,flag,carry,chain,
                                    controls=controls,geq=False)
    old.one_bit_bypass_constant_add(qc,target,-d,controls,carry,chain)
    old.one_bit_bypass_constant_add(qc,target,+modulus,[flag],carry,chain)
    best.public_threshold_predicate(qc,target,k,flag,carry,chain,
                                    controls=controls,geq=True)


def source_add_circuit(k,implementation):
    enable=QuantumRegister(1,"enable")
    target=QuantumRegister(BITS,"target")
    wrap=QuantumRegister(1,"wrap")
    carry=QuantumRegister(BITS,"carry")
    scratch=QuantumRegister(BITS+3,"scratch")
    qc=QuantumCircuit(enable,target,wrap,carry,scratch)
    chosen=POSITIVE_MODADD if implementation=="positive" else signed_all_k_modadd
    chosen(qc,target,k,N,[enable[0]],wrap[0],carry,scratch)
    return qc,dict(enable=list(enable),target=list(target),wrap=list(wrap),
                   carry=list(carry),scratch=list(scratch))


def source_gate_cost(ops):
    allowed={"x","cx","ccx","rccx"}
    if set(ops)-allowed:raise AssertionError("Unexpected source instruction: "+str(ops))
    return int(ops.get("cx",0)+6*ops.get("ccx",0)+3*ops.get("rccx",0))


def prebackend_static_source_selector():
    """Score source gates, no target compiler, k-only deterministic rule."""
    mapping={}
    detail=[]
    original_specs={}
    signed_specs={}
    for k in range(1,N):
        orig,oreg=source_add_circuit(k,"positive")
        alt,areg=source_add_circuit(k,"signed")
        oc={str(key):int(num) for key,num in orig.count_ops().items()}
        ac={str(key):int(num) for key,num in alt.count_ops().items()}
        op=source_gate_cost(oc)
        sp=source_gate_cost(ac)
        choice="signed" if sp<op else "positive"
        mapping[k]=choice
        original_specs[k]=(orig,oreg)
        signed_specs[k]=(alt,areg)
        detail.append(dict(public_k=k,positive_gate_counts=oc,
                           signed_gate_counts=ac,
                           positive_static_proxy=op,signed_static_proxy=sp,
                           selected_branch=choice,
                           signed_strictly_less_two_qubit_source_proxy=(sp<op)))
    assert len(mapping)==34
    assert all(z["selected_branch"]==(
        "signed" if z["signed_static_proxy"]<z["positive_static_proxy"] else "positive")
        for z in detail)
    return mapping,detail,original_specs,signed_specs


def standalone_public_arithmetic_identity():
    cases=0
    for k in range(1,N):
        d=N-k
        for enabled in (0,1):
            for x in range(N if enabled else 64):
                orig=(x+k)%N if enabled else x
                if enabled:
                    under=x<d
                    output=((x-d)%64 + (N if under else 0))%64
                    flag_uncompute=(output>=k)
                    assert flag_uncompute==under,(k,x,output,under)
                else:
                    output=x
                assert output==orig,(k,x,enabled,output,orig)
                cases+=1
    assert cases==34*99
    return dict(pass_all=True,all_public_k_1_through_34=True,
                six_bit_disabled_identity=True,
                enabled_values_all_0_through_34=True,
                cases=cases,underflow_cleanup_exact_for_every_valid_k=True)


def quantum_phase_per_k_adds(positives,signeds):
    """Interpret ACTUAL emitted monomial complex source unitary for all 2*34*99."""
    total=0
    proof_by_k=[]
    for k in range(1,N):
        checked={}
        for label,storage in (("positive",positives),("signed",signeds)):
            qc,regs=storage[k]
            idx,instructions,ops=previous.actual_complex_instructions(qc)
            ep=idx[regs["enable"][0]]
            positions=[idx[z] for z in regs["target"]]
            aux=[idx[z] for name in ("wrap","carry","scratch") for z in regs[name]]
            cases=0
            for enabled in (0,1):
                for x in range(N if enabled else 64):
                    inp=(enabled<<ep)
                    for j,p in enumerate(positions):
                        inp|=((x>>j)&1)<<p
                    end,amplitude=previous.evolve_basis(instructions,inp)
                    got=sum(((end>>p)&1)<<j for j,p in enumerate(positions))
                    want=(x+k)%N if enabled else x
                    if got!=want or ((end>>ep)&1)!=enabled:
                        raise AssertionError(json.dumps(dict(
                          stage="per-public-k-quantum-add",
                          k=k,implementation=label,x=x,enabled=enabled,
                          got=got,want=want)))
                    if any((end>>p)&1 for p in aux):
                        raise AssertionError(f"Dirty wrap/carry/scratch for k={k} x={x} {label}")
                    previous.check_exact_phase(amplitude,
                        f"public k={k} x={x} active={enabled} branch={label}")
                    cases+=1
            assert cases==99
            checked[label]=dict(pass_all=True,cases=cases,
                                phase_exact_plus_one=True,all_aux_clean=True,
                                actual_source_gates=ops)
            total+=cases
        proof_by_k.append(dict(public_k=k,positive=checked["positive"],
                               signed=checked["signed"]))
    assert total==6732 and len(proof_by_k)==34
    return dict(pass_all=True,total_quantum_operator_basis_cases=total,
                per_public_k=proof_by_k,
                exact_complex_phase_plus_one=True,all_aux_clean=True,
                every_public_constant_both_branches_verified=True)


def structural_selected_modadd(qc,target,k,modulus,controls,flag,carry,chain):
    """Build using just immutable public k table (never base or backend scores)."""
    global SIGNED_CALLS,POSITIVE_CALLS
    k=int(k)%int(modulus)
    if not k:return
    selected=SELECTION.get(k)
    if selected=="signed":
        SIGNED_CALLS+=1
        return signed_all_k_modadd(qc,target,k,modulus,controls,flag,carry,chain)
    if selected=="positive":
        POSITIVE_CALLS+=1
        return POSITIVE_MODADD(qc,target,k,modulus,controls,flag,carry,chain)
    raise AssertionError("Public k not in frozen source selector")


def public_weighted_constants(base):
    inv=pow(base,-1,N)
    return [(base*(1<<i))%N for i in range(BITS)]+[
          (-inv*(1<<i))%N for i in range(BITS)]


def prove_whole_source_variants(base,mapping):
    global SIGNED_CALLS,POSITIVE_CALLS,SELECTION
    # First baseline ORIGINAL robust public one-bit-bypass source:
    best.optimized_modadd=POSITIVE_MODADD
    primitive.modadd=POSITIVE_MODADD
    original_qc,original_regs=previous.verified.build(base)
    original_proof=previous.exhaustive_full_multiplier_phases(
        original_qc,original_regs,base)
    old_source=HISTORICAL[base]["source"]
    assert original_qc.num_qubits==32
    assert original_proof["pass_all"] and original_proof["full_residue_control_basis_cases"]==128
    assert original_proof["all_25_auxiliaries_clean"]
    assert original_proof["exact_complex_output_phase_plus_one"]
    assert original_proof["quantum_source_gate_counts"]==old_source,(
        original_proof["quantum_source_gate_counts"],old_source)

    # Candidate source same layout, only public per-k source selector:
    SELECTION=dict(mapping)
    SIGNED_CALLS=0
    POSITIVE_CALLS=0
    primitive.modadd=structural_selected_modadd
    best.optimized_modadd=structural_selected_modadd
    selected_qc,selected_regs=previous.verified.build(base)
    signed_calls=SIGNED_CALLS
    positive_calls=POSITIVE_CALLS
    new_proof=previous.exhaustive_full_multiplier_phases(
        selected_qc,selected_regs,base)
    assert selected_qc.num_qubits==32
    assert new_proof["pass_all"] and new_proof["full_residue_control_basis_cases"]==128
    assert new_proof["all_25_auxiliaries_clean"] and new_proof["exact_complex_output_phase_plus_one"]
    if signed_calls+positive_calls!=12:
        raise AssertionError(f"Source whole weighted count wrong: {signed_calls}+{positive_calls}")
    expected_signed=sum(mapping[k]=="signed" for k in public_weighted_constants(base))
    if expected_signed!=signed_calls:
        raise AssertionError("Selector not applied by public constant only")
    assert all(name in ("x","cx","ccx","rccx")
               for name in new_proof["quantum_source_gate_counts"])
    proof=dict(pass_all=True,original_full=original_proof,
        candidate_full=new_proof,
        actual_signed_weighted_additions=signed_calls,
        actual_positive_weighted_additions=positive_calls,
        weighted_public_constants=public_weighted_constants(base),
        selection_for_each_weight=[mapping[k] for k in public_weighted_constants(base)],
        no_true_order_or_orbit_or_factor_inputs=True,
        both_source_circuits_32_qubits=True,
        both_return_all_25_ancillas_clean=True,
        both_full_input_complex_phases_exactly_plus_one=True)
    return original_qc,selected_qc,proof


def native_compile(pm,circuit):
    start=time.perf_counter()
    native=pm.run(circuit)
    ops={str(x):int(v) for x,v in native.count_ops().items()}
    elapsed=time.perf_counter()-start
    cz=ops.get("cz",0)
    depth=int(native.depth())
    assert cz>0 and depth>0 and native.num_qubits>=32
    return dict(cz=cz,depth=depth,native_ops=ops,
      device_width=int(native.num_qubits),native_size=int(native.size()),
      compiler_seconds=elapsed)


def summary(rows,changed):
    assert len(rows)==8
    dc=[r["candidate_minus_original"]["cz"] for r in rows]
    dd=[r["candidate_minus_original"]["depth"] for r in rows]
    wins=sum(c<0 and d<0 for c,d in zip(dc,dd))
    medc=statistics.median(dc)
    medd=statistics.median(dd)
    return dict(total_seed_pairs=len(rows),
       joint_cz_depth_improvement_seed_count=wins,
       cz_improvement_seeds=sum(c<0 for c in dc),
       depth_improvement_seeds=sum(d<0 for d in dd),
       median_paired_cz_delta=medc,median_paired_depth_delta=medd,
       min_paired_cz_delta=min(dc),max_paired_cz_delta=max(dc),
       min_paired_depth_delta=min(dd),max_paired_depth_delta=max(dd),
       joint_win_rule_at_least_six=(wins>=6),
       paired_cz_and_depth_medians_negative=(medc<0 and medd<0),
       weighted_modadd_source_changes_nonzero=(changed>0),
       every_seed_reported=True)


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f"qrr_n35_static_sign_selector_base{base}.json"
    rec=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
      utc=datetime.now(timezone.utc).isoformat(),
      preregistration="docs/QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_PREREG.md",
      N=N,base=base,seeds=list(SEEDS),
      experiment="34 constant-local public source CZ proxy sign selector vs true two-base robust one-bit bypass",
      source_score_formula="cx+6*ccx+3*rccx; x excluded; ties choose positive",
      read_only_ibm_fez_native_target=True,
      compiler_optimization_level=1,transpiler_target="ibm_fez",
      original_historical_8776=HISTORICAL[base],
      source_full_residue_and_all_25_ancillas_clean_required=True,
      source_quantum_exact_phase_plus_one_required=True,
      hardware_cz_limit=800,hardware_depth_limit=2000,
      true_multiplicative_order_not_used=True,public_orbit_not_compiled=True,
      private_prime_factors_not_used=True,
      qpu_jobs_submitted=0,quantum_runtime_used=False,paid_runtime_used=False,
      matched_seed_pairs=[],status="STARTED",success=False)
    def save():
        path.write_text(json.dumps(rec,indent=2,default=str)+"\n")
    save()
    try:
        bootstrap_original_best()
        ident=standalone_public_arithmetic_identity()
        inverse=dm.boolean_and_inverse_operator_proof()
        comparator=dm.exhaustive_demorgan_comparator_phase_proof()
        assert comparator["pass_all"] and comparator["actual_emitted_gate_cases"]==42672
        assert comparator["final_complex_phase_plus_one_every_case"]

        mapping,scores,positive_circuits,signed_circuits=prebackend_static_source_selector()
        rec["prebackend_public_k_source_score_table"]=scores
        rec["public_k_sign_selection"]={str(k):mapping[k] for k in sorted(mapping)}
        rec["selector_static_score_summary"]=dict(
            all_34_public_k_scored=True,
            signed_constants=[k for k in sorted(mapping) if mapping[k]=="signed"],
            positive_constants=[k for k in sorted(mapping) if mapping[k]=="positive"],
            signed_count=sum(x=="signed" for x in mapping.values()),
            positive_count=sum(x=="positive" for x in mapping.values()),
            tie_preference="positive",
            source_weights=dict(cx=1,ccx=6,rccx=3,x=0))
        save()
        per_k=quantum_phase_per_k_adds(positive_circuits,signed_circuits)
        assert per_k["pass_all"] and per_k["total_quantum_operator_basis_cases"]==6732
        original_qc,candidate_qc,whole=prove_whole_source_variants(base,mapping)
        rec["prebackend_exact_quantum_gate_proofs"]=dict(
            public_identity=ident,demorgan_inverse=inverse,
            unchanged_comparator=comparator,
            both_branches_per_k=per_k,whole_full_multiplier=whole,
            everything_complex_phase_exactly_plus_one=True,
            all_helpers_clean=True)
        rec["status"]="PREBACKEND_SOURCE_OPERATOR_PROOFS_PASS"
        save()
        print("N35 PUBLIC STATIC SIGN SELECTOR",base,
            "all34 rule",json.dumps(rec["selector_static_score_summary"],sort_keys=True),
            "source whole signed/positive",
            whole["actual_signed_weighted_additions"],whole["actual_positive_weighted_additions"],
            "phase+1 identity3366 comparator42672 per-k6732 full128+128",
            "NO QPU",flush=True)

        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Fez backend is not an adequate native hardware target")
        rec["fez_device_qubits"]=int(backend.num_qubits)
        rec["status"]="CPU_ONLY_EIGHT_MATCHED_NATIVE_SEEDS"
        save()

        for seed in SEEDS:
            pm=generate_preset_pass_manager(
                backend=backend,optimization_level=1,seed_transpiler=seed)
            origin=native_compile(pm,original_qc)
            cand=native_compile(pm,candidate_qc)
            delta=dict(cz=cand["cz"]-origin["cz"],depth=cand["depth"]-origin["depth"])
            row=dict(seed=seed,original=origin,candidate=cand,
                candidate_minus_original=delta,
                both_cz_and_depth_strictly_improve=(delta["cz"]<0 and delta["depth"]<0),
                original_hardware_feasible=(origin["cz"]<=800 and origin["depth"]<=2000),
                candidate_hardware_feasible=(cand["cz"]<=800 and cand["depth"]<=2000))
            rec["matched_seed_pairs"].append(row)
            save()
            print("STATIC SIGN SOURCE FEZ CPU",base,seed,
                "ORIGINAL",origin["cz"],origin["depth"],
                "RULE",cand["cz"],cand["depth"],
                "DELTA",delta["cz"],delta["depth"],
                "JOINT",row["both_cz_and_depth_strictly_improve"],
                "HARDWARE",row["candidate_hardware_feasible"],"NO QPU",flush=True)

        summ=summary(rec["matched_seed_pairs"],whole["actual_signed_weighted_additions"])
        historical=HISTORICAL[base]
        anchor=next(x for x in rec["matched_seed_pairs"] if x["seed"]==8776)
        reproduced=(anchor["original"]["cz"]==historical["cz"] and
                    anchor["original"]["depth"]==historical["depth"])
        summ["original_8776_anchor_exact"]=reproduced
        summ["original_anchor_drift"]=not reproduced
        summ["robust_gate_per_base_pass"]=bool(
           reproduced and summ["weighted_modadd_source_changes_nonzero"] and
           summ["joint_win_rule_at_least_six"] and
           summ["paired_cz_and_depth_medians_negative"])
        summ["all_source_and_candidate_layouts_fail_hardware_gate"]=all(
             not x["original_hardware_feasible"] and not x["candidate_hardware_feasible"]
             for x in rec["matched_seed_pairs"])
        rec.update(summary=summ,status="COMPILE_SUCCESS",success=True,
                   all_16_native_cpu_compiles_complete=True)
        save()
        print("STATIC PUBLIC SIGN 8SEED SUMMARY",base,json.dumps(summ,sort_keys=True),
              "NO QPU",flush=True)
        return 0
    except Exception as exc:
        rec.update(status="FAIL",success=False,
            error_type=type(exc).__name__,
            error_message=str(exc)[:1800],
            error_traceback=traceback.format_exc()[-3200:],
            qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print("STATIC SIGN SOURCE EXPERIMENT FAIL",base,type(exc).__name__,
              str(exc)[:950],traceback.format_exc()[-1400:],"NO QPU",flush=True)
        return 1


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(ap.parse_args().base))
