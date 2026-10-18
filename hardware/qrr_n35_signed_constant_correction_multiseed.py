#!/usr/bin/env python3
"""Frozen N35 public signed modular-constant representation, 8 matched seeds.

Research lead Chase Lunsford / CaMaLabs. Against the verified public
one-bit carry bypass + De Morgan zero-CX comparator baseline, only change
conditional modular addition for k>35//2: subtract d=35-k, conditionally
correct by +35, and uncompute underflow flag on output >=35-d.
True same reversible full-residue controlled modmul, exact complex source
phase verification BEFORE ibm_fez backend target READ, zero hardware jobs.
"""
from __future__ import annotations
import argparse,json,os,time,traceback,statistics
from pathlib import Path
from datetime import datetime,timezone

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_public_one_bit_carry_bypass_multiseed as old

dm=old.dm
previous=old.previous
primitive=old.primitive
best=old.best
N=35
BITS=6
BASES=(2,8)
SEEDS=(11,37,101,409,8776,12011,20261,45673)
REV="qrr-n35-signed-public-constant-modadd-eight-seeds-v1-20261018"
ROOT=Path("results/ibm_shor35_signed_constant_correction")
HISTORICAL={
    2:dict(cz=7887,depth=18221,
      source=dict(cx=303,rccx=596,x=1738,ccx=160)),
    8:dict(cz=7802,depth=18449,
      source=dict(cx=311,rccx=616,x=1828,ccx=162))
}
COUNTER={"signed":0,"unchanged":0}
ORIGINAL_BEST_MODADD=best.optimized_modadd


def public_signed_arithmetic_identity():
    """Verify signed/underflow logic for ALL k and valid/disabled data."""
    tests=0
    negatives=0
    positives=0
    for k in range(1,N):
        for enabled in (0,1):
            for x in range(64 if not enabled else N):
                if k>N//2 and enabled:
                    d=N-k
                    flag=(x<d)
                    unsigned_intermediate=(x-d)%64
                    result=(unsigned_intermediate+(N if flag else 0))%64
                    cleanup_condition=(result>=N-d)
                    if flag!=cleanup_condition:
                        raise AssertionError(json.dumps(dict(
                            error="underflow/cleanup predicate disagree",
                            k=k,x=x,d=d,result=result,flag=flag,cleanup_condition=cleanup_condition)))
                    negatives+=1
                elif enabled:
                    result=(x+k)%N
                    positives+=1
                else:
                    result=x
                expected=(x+k)%N if enabled else x
                if result!=expected:
                    raise AssertionError(json.dumps(dict(
                        error="bad signed modular addition identity",
                        k=k,x=x,enabled=enabled,result=result,expected=expected)))
                tests+=1
    assert tests==34*99 and negatives>0 and positives>0
    for base in BASES:
        inv=pow(base,-1,N)
        weighted=[(base*(1<<i))%N for i in range(BITS)]
        weighted +=[(-inv*(1<<i))%N for i in range(BITS)]
        assert len(weighted)==12 and sum(k>N//2 for k in weighted)==7,(base,weighted)
    return dict(pass_all=True,all_public_k_1_to_34=True,
         all_enabled_valid_x_and_all_disabled_sixbit_x=True,
         public_test_cases=tests,signed_case_count=negatives,
         positive_case_count=positives,
         underflow_flag_cleanup_logic_verified=True,
         seven_signed_weighted_additions_per_public_base=True)


def signed_public_modadd(qc,target,k,modulus,controls,flag,carry,chain):
    """One frozen public k-dependent alternate representation, same unitary.

    The flag is always CLEAN on entry and exit, and all predicate carry bits
    are separately fully uncomputed by the unchanged phase-safe comparator.
    Uses ONLY public k and public N; no state/orbit/order lookup.
    """
    k=int(k)%modulus
    if k==0:return
    controls=list(controls)
    if k<=modulus//2:
        COUNTER["unchanged"]+=1
        return ORIGINAL_BEST_MODADD(qc,target,k,modulus,controls,flag,carry,chain)
    COUNTER["signed"]+=1
    d=modulus-k
    # Compute enabled underflow flag on ORIGINAL x.
    best.public_threshold_predicate(qc,target,d,flag,carry,chain,
                                    controls=controls,geq=False)
    # Descending prefix-carry add is defined on ALL 6-bit values mod64.
    # The same independently verified one-bit bypass is kept unchanged.
    old.one_bit_bypass_constant_add(qc,target,-d,controls,carry,chain)
    old.one_bit_bypass_constant_add(qc,target,+modulus,[flag],carry,chain)
    # Wrapped outputs occupy [modulus-d,modulus-1], nonwrapped [0,modulus-d-1].
    best.public_threshold_predicate(qc,target,modulus-d,flag,carry,chain,
                                    controls=controls,geq=True)


def source_proofs_before_backend(base):
    """Build and prove BOTH actual Qiskit source circuits before reading Fez."""
    old.ensure_strong_demorgan_baseline()
    best.constant_add_from_prefix_carry=old.one_bit_bypass_constant_add
    # Original module/circuit exactly as previously gate- and seed-verified.
    primitive.modadd=ORIGINAL_BEST_MODADD
    best.optimized_modadd=ORIGINAL_BEST_MODADD

    arithmetic=public_signed_arithmetic_identity()
    demorgan_identity=dm.boolean_and_inverse_operator_proof()
    cmp=dm.exhaustive_demorgan_comparator_phase_proof()
    if not (cmp["pass_all"] and cmp["actual_emitted_gate_cases"]==42672
            and cmp["final_complex_phase_plus_one_every_case"]):
        raise AssertionError("Original De Morgan comparator phase control not correct")
    original_modadd=previous.exhaustive_modadd_phases(previous.source_constants())
    assert original_modadd["pass_all"] and original_modadd["source_gate_cases"]==1584
    assert original_modadd["exact_complex_phase_plus_one"]
    old_qc,old_regs=previous.verified.build(base)
    old_full=previous.exhaustive_full_multiplier_phases(old_qc,old_regs,base)
    assert old_full["pass_all"] and old_full["full_residue_control_basis_cases"]==128
    assert old_full["all_25_auxiliaries_clean"] and old_full["exact_complex_output_phase_plus_one"]
    assert old_qc.num_qubits==32
    if old_full["quantum_source_gate_counts"]!=HISTORICAL[base]["source"]:
        raise AssertionError(json.dumps(dict(
          original_frozen_source_changed=True,base=base,
          expected=HISTORICAL[base]["source"],
          observed=old_full["quantum_source_gate_counts"])))
    # Candidate differs ONLY in public k>N//2 branch of the same modadd call.
    best.optimized_modadd=signed_public_modadd
    primitive.modadd=signed_public_modadd
    COUNTER["signed"]=0
    COUNTER["unchanged"]=0
    new_modadd=previous.exhaustive_modadd_phases(previous.source_constants())
    assert new_modadd["pass_all"] and new_modadd["source_gate_cases"]==1584
    assert new_modadd["exact_complex_phase_plus_one"]
    COUNTER["signed"]=0
    COUNTER["unchanged"]=0
    new_qc,new_regs=previous.verified.build(base)
    signed_calls=COUNTER["signed"]
    unchanged_calls=COUNTER["unchanged"]
    if signed_calls!=7 or unchanged_calls!=5:
        raise AssertionError(json.dumps(dict(
           expected_7_signed_and_5_positive=True,actual_signed=signed_calls,
           actual_unchanged=unchanged_calls,base=base)))
    new_full=previous.exhaustive_full_multiplier_phases(new_qc,new_regs,base)
    assert new_full["pass_all"] and new_full["full_residue_control_basis_cases"]==128
    assert new_full["all_25_auxiliaries_clean"] and new_full["exact_complex_output_phase_plus_one"]
    assert new_qc.num_qubits==32
    new_ops=new_full["quantum_source_gate_counts"]
    if new_ops==HISTORICAL[base]["source"]:
        raise AssertionError("Chosen source arithmetic branch not exercised, identical gate counts")
    if not ({"x","cx","ccx","rccx"}==set(new_ops)):
        raise AssertionError("Unexpected emitted gate alphabet in signed candidate")
    print("N35 PUBLIC SIGNED SOURCE GATES PASS",base,
      "classical",arithmetic["public_test_cases"],
      "CMP",cmp["actual_emitted_gate_cases"],
      "MODADD original/candidate",original_modadd["source_gate_cases"],new_modadd["source_gate_cases"],
      "WHOLE original/candidate",old_full["full_residue_control_basis_cases"],
      new_full["full_residue_control_basis_cases"],
      "SIGNED",signed_calls,"UNCHANGED",unchanged_calls,
      "SOURCE original",HISTORICAL[base]["source"],"new",new_ops,
      "complex +1 quantum phase, 25 CLEAN",flush=True)
    proof=dict(pass_all=True,public_signed_identity=arithmetic,
      demorgan_boolean_and_rccx_inverse_proof=demorgan_identity,
      unchanged_comparator_phase_proof=cmp,
      baseline_modadd_phase_proof=original_modadd,
      signed_modadd_phase_proof=new_modadd,
      baseline_full_multiplier_phase_proof=old_full,
      signed_full_multiplier_phase_proof=new_full,
      actual_signed_k_above_half_branch_calls=signed_calls,
      actual_unchanged_small_k_branch_calls=unchanged_calls,
      candidate_source_gate_counts=new_ops,
      original_source_gate_counts=HISTORICAL[base]["source"],
      both_circuits_32_logical_qubits=True,
      both_circuits_all_25_aux_clean=True,
      exact_complex_quantum_output_phase_plus_one_for_both=True)
    return old_qc,new_qc,proof


def cpu_compile(pm,qc):
    """Same Qiskit Fez TARGET compiler object within each seed pair, no QPU."""
    start=time.perf_counter()
    native=pm.run(qc)
    sec=time.perf_counter()-start
    ops={str(name):int(value) for name,value in native.count_ops().items()}
    cz=int(ops.get("cz",0));depth=int(native.depth())
    if not (cz>0 and depth>0 and native.num_qubits>=qc.num_qubits):
        raise AssertionError("CPU ISA compilation returned invalid metrics")
    return dict(cz=cz,depth=depth,
       native_count_ops=ops,
       compiled_device_width=int(native.num_qubits),
       native_size=int(native.size()),
       compiler_seconds=sec)


def summarize(rows):
    assert len(rows)==len(SEEDS)
    dc=[row["candidate_minus_baseline"]["cz"] for row in rows]
    dd=[row["candidate_minus_baseline"]["depth"] for row in rows]
    both=sum(c<0 and d<0 for c,d in zip(dc,dd))
    cz_med=statistics.median(dc)
    depth_med=statistics.median(dd)
    return dict(seeds=len(rows),both_metric_strict_win_seeds=both,
       cz_win_seeds=sum(z<0 for z in dc),depth_win_seeds=sum(z<0 for z in dd),
       paired_median_cz_delta=cz_med,paired_median_depth_delta=depth_med,
       paired_min_cz_delta=min(dc),paired_max_cz_delta=max(dc),
       paired_min_depth_delta=min(dd),paired_max_depth_delta=max(dd),
       six_of_eight_joint_win_gate=both>=6,
       both_median_deltas_strictly_negative=(cz_med<0 and depth_med<0),
       no_seeds_excluded=True)


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    output=ROOT/f"qrr_n35_signed_correction_base{base}.json"
    rec=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
      utc=datetime.now(timezone.utc).isoformat(),
      preregistration="docs/QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_PREREG.md",
      experiment="public k>17 signed correction against robust public one-bit bypass",
      N=N,base=base,seeds=list(SEEDS),
      original_robust_seed8776=HISTORICAL[base],
      read_only_native_backend="ibm_fez",compiler_optimization_level=1,
      immutable_device_cz_limit=800,immutable_device_depth_limit=2000,
      full_residue_six_bit_work_and_control=True,
      original_robust_arithmetic_preserved_except_signed_rule=True,
      true_order_not_used=True,private_factors_not_used=True,
      precomputed_orbit_not_used=True,
      quantum_runtime_used=False,paid_quantum_runtime_used=False,qpu_jobs_submitted=0,
      matched_seed_pairs=[],
      status="STARTED",success=False)
    def save():output.write_text(json.dumps(rec,indent=2,default=str)+"\n")
    save()
    try:
        baseline,candidate,proof=source_proofs_before_backend(base)
        rec["quantum_source_proofs"]=proof
        rec["status"]="QUANTUM_PHASE_PROOFS_PASS"
        save()
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Fez target simulator or too few qubits")
        rec["target_device_width"]=int(backend.num_qubits)
        rec["status"]="CPU_NATIVE_8_SEED_PAIRS"
        save()
        for seed in SEEDS:
            pm=generate_preset_pass_manager(backend=backend,
                optimization_level=1,seed_transpiler=seed)
            b=cpu_compile(pm,baseline)
            c=cpu_compile(pm,candidate)
            dc=c["cz"]-b["cz"];dd=c["depth"]-b["depth"]
            row=dict(seed=seed,baseline=b,candidate=c,
                 candidate_minus_baseline=dict(cz=dc,depth=dd),
                 strict_both_improve=(dc<0 and dd<0),
                 baseline_device_feasible=(b["cz"]<=800 and b["depth"]<=2000),
                 candidate_device_feasible=(c["cz"]<=800 and c["depth"]<=2000))
            rec["matched_seed_pairs"].append(row)
            save()
            print("SIGNED MOD35 MATCHED FEZ NATIVE CPU",base,seed,
                 "OLD",b["cz"],b["depth"],"SIGNED",c["cz"],c["depth"],
                 "DELTA",dc,dd,"BOTH",row["strict_both_improve"],
                 "HARDWARE",row["candidate_device_feasible"],"NO QPU",flush=True)
        summary=summarize(rec["matched_seed_pairs"])
        anchor=next(row for row in rec["matched_seed_pairs"] if row["seed"]==8776)
        historical=HISTORICAL[base]
        anchor_exact=(anchor["baseline"]["cz"]==historical["cz"] and
                      anchor["baseline"]["depth"]==historical["depth"])
        summary["original_seed8776_reproduced_exact"]=anchor_exact
        summary["historical_anchor_drift"]=not anchor_exact
        summary["robust_engineering_per_base_pass"]=bool(anchor_exact and
              summary["six_of_eight_joint_win_gate"] and
              summary["both_median_deltas_strictly_negative"])
        summary["all_layouts_fail_immutable_device_gate"]=all(
              not x["baseline_device_feasible"] and not x["candidate_device_feasible"]
              for x in rec["matched_seed_pairs"])
        rec.update(status="COMPILE_SUCCESS",success=True,
            summary=summary,all_32_native_compilations_in_joint_two_base_run=True,
            no_quantum_device_jobs=True)
        save()
        print("PUBLIC SIGNED CORRECTION 8-SEED SUMMARY",base,
             json.dumps(summary,sort_keys=True),"NO QPU",flush=True)
        return 0
    except Exception as e:
        rec.update(status="FAIL",success=False,failure_type=type(e).__name__,
             failure_message=str(e)[:1500],
             failure_traceback=traceback.format_exc()[-2600:],
             qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print("N35 PUBLIC SIGNED EXPERIMENT FAIL",base,
             type(e).__name__,str(e)[:750],
             traceback.format_exc()[-1500:],"NO QPU",flush=True)
        return 1


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",required=True,type=int,choices=BASES)
    raise SystemExit(main(ap.parse_args().base))
