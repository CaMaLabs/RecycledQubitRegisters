#!/usr/bin/env python3
"""N35 fixed-public-constant 1-bit carry bypass on proven De Morgan arithmetic.

Research lead Chase Lunsford / CaMaLabs.
ONE difference between eight-seed matched Qiskit source circuits: when
carry threshold for public +v into output bit j is exactly 2**(j-1),
copy original input bit j-1 as the carry control directly, instead of
compute/uncompute a redundant 1-bit comparator ancilla (two CX eliminated).

The original De Morgan comparator and phase-exact temporary RCCX carry gates
remain unchanged. BEFORE backend access verify Qiskit emitted complex +1
quantum amplitudes on both circuit variants and every relevant basis input.
CPU-only Fez TARGET compilation. ZERO REAL QPU JOBS/RUNTIME.
"""
from __future__ import annotations

import argparse,json,os,time,traceback,statistics
from pathlib import Path
from datetime import datetime,timezone

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_demorgan_zero_cx_or_multiseed as dm

previous=dm.previous
primitive=dm.primitive
best=previous.best
BASES=(2,8)
N=35
BITS=6
SEEDS=(11,37,101,409,8776,12011,20261,45673)
ROOT=Path("results/ibm_shor35_one_bit_carry_bypass_multiseed")
REV="qrr-n35-one-bit-carry-bypass-demorgan-eight-matched-seeds-v1-20261018"

HISTORICAL={
  2:dict(
      baseline=dict(cz=7993,depth=18604,
          source=dict(cx=349,rccx=596,x=1738,ccx=160)),
      candidate_source=dict(cx=303,rccx=596,x=1738,ccx=160),
      carry_bypasses=23),
  8:dict(
      baseline=dict(cz=8758,depth=20575,
          source=dict(cx=357,rccx=616,x=1828,ccx=162)),
      candidate_source=dict(cx=311,rccx=616,x=1828,ccx=162),
      carry_bypasses=23)
}

ORIGINAL_CONSTANT_ADD=best.constant_add_from_prefix_carry
CANDIDATE_COUNTER={"bypasses":0}


def public_carry_identity_exhaustive():
    """Independent binary identity for all public v, j and possible low bits."""
    cases=0
    hits=0
    for v in range(1<<BITS):
        for j in range(1,BITS):
            bit=1<<(j-1)
            low=v&((1<<j)-1)
            eligible=(low==bit)
            if eligible:
                hits+=1
                threshold=(1<<j)-low
                assert threshold==bit
                for xlow in range(1<<j):
                    got=int(xlow>=threshold)
                    expected=(xlow>>(j-1))&1
                    if got!=expected:
                        raise AssertionError(
                            f"Public single-bit carry identity failed v={v} j={j} xlow={xlow}")
                    cases+=1
    if cases<=0 or hits<=0:
        raise AssertionError("Public low-bit formula intervention not exercised")
    return dict(pass_all=True,
       every_public_six_bit_constant_tested=True,
       all_carry_thresholds_power_half_tested=True,
       matching_public_v_and_output_bit_pairs=hits,
       exhaustive_low_prefix_cases=cases,
       comparator_equivalent_to_single_original_bit=True)


def one_bit_bypass_constant_add(qc,target,value,controls,carry,chain):
    """Exact source difference; descend output bit j before changing low bits."""
    target=list(target)
    controls=list(controls)
    n=len(target)
    v=int(value)%(1<<n)
    for j in range(n-1,-1,-1):
        low=v&((1<<j)-1)
        if low:
            threshold=(1<<j)-low
            if j>=1 and low==(1<<(j-1)):
                # For threshold==half of low-j unsigned range,
                # input_low_j>=half iff input[j-1]==1.
                primitive.multi_x(qc,controls+[target[j-1]],target[j],chain)
                CANDIDATE_COUNTER["bypasses"]+=1
            else:
                best.public_threshold_predicate(qc,target[:j],threshold,
                    target[j],carry[:j],chain,controls=controls,geq=True)
        if (v>>j)&1:
            primitive.multi_x(qc,controls,target[j],chain)


def ensure_strong_demorgan_baseline():
    """Patch only previous predicate to the already verified best comparator."""
    primitive.predicate=dm.demorgan_ripple_predicate
    primitive.modadd=best.optimized_modadd
    best.constant_add_from_prefix_carry=ORIGINAL_CONSTANT_ADD


def prove_source_variants_before_target(base):
    if base not in BASES:raise ValueError("Unsupported public base")
    ensure_strong_demorgan_baseline()
    identity=public_carry_identity_exhaustive()
    dm_inverse=dm.boolean_and_inverse_operator_proof()

    compare=dm.exhaustive_demorgan_comparator_phase_proof()
    assert compare["pass_all"] and compare["actual_emitted_gate_cases"]==42672
    assert compare["final_complex_phase_plus_one_every_case"]

    baseline_add=previous.exhaustive_modadd_phases(previous.source_constants())
    assert baseline_add["pass_all"] and baseline_add["source_gate_cases"]==1584
    assert baseline_add["exact_complex_phase_plus_one"]
    baseline_qc,base_regs=previous.verified.build(base)
    baseline_proof=previous.exhaustive_full_multiplier_phases(baseline_qc,base_regs,base)
    old=HISTORICAL[base]
    assert baseline_qc.num_qubits==32
    assert baseline_proof["quantum_source_gate_counts"]==old["baseline"]["source"]
    assert baseline_proof["full_residue_control_basis_cases"]==128
    assert baseline_proof["pass_all"] and baseline_proof["all_25_auxiliaries_clean"]
    assert baseline_proof["exact_complex_output_phase_plus_one"]
    print("BASELINE DEMORGAN COMPLEX GATES",base,
          "CMP 42672 MODADD 1584 FULL 128 source",baseline_proof["quantum_source_gate_counts"],
          "ALL +1 PHASE 25 CLEAN",flush=True)

    # All prior literal instructions already materialized; patch only the
    # public constant adder used by the candidate. Comparator stays IDENTICAL.
    best.constant_add_from_prefix_carry=one_bit_bypass_constant_add
    CANDIDATE_COUNTER["bypasses"]=0
    candidate_add=previous.exhaustive_modadd_phases(previous.source_constants())
    assert candidate_add["pass_all"] and candidate_add["source_gate_cases"]==1584
    assert candidate_add["exact_complex_phase_plus_one"]
    CANDIDATE_COUNTER["bypasses"]=0
    candidate_qc,candidate_regs=previous.verified.build(base)
    bypasses=CANDIDATE_COUNTER["bypasses"]
    candidate_proof=previous.exhaustive_full_multiplier_phases(candidate_qc,candidate_regs,base)
    assert candidate_qc.num_qubits==32
    assert candidate_proof["full_residue_control_basis_cases"]==128
    assert candidate_proof["pass_all"] and candidate_proof["all_25_auxiliaries_clean"]
    assert candidate_proof["exact_complex_output_phase_plus_one"]
    if bypasses!=old["carry_bypasses"]:
        raise AssertionError(json.dumps(dict(
            source_bypass_missing_or_extra=True,base=base,
            got=bypasses,expected=old["carry_bypasses"])))
    now=candidate_proof["quantum_source_gate_counts"]
    if now!=old["candidate_source"]:
        raise AssertionError(json.dumps(dict(
            source_only_46_cx_intervention_failed=True,base=base,
            got=now,expected=old["candidate_source"])))
    print("CANDIDATE PUBLIC SINGLE-BIT CARRY",base,
          "CONST IDENTITY",identity["exhaustive_low_prefix_cases"],
          "CMP",compare["actual_emitted_gate_cases"],
          "MODADD",candidate_add["source_gate_cases"],
          "FULL",candidate_proof["full_residue_control_basis_cases"],
          "BYPASSES",bypasses,"SOURCE",now,
          "ALL COMPLEX PHASE+1, 25 CLEAN ZERO QPU",flush=True)

    proof=dict(pass_all=True,public_carry_identity=identity,
        demorgan_inverse_operator_proof=dm_inverse,
        unchanged_demorgan_comparator_phase_proof=compare,
        baseline_modadd_phase_proof=baseline_add,
        candidate_modadd_phase_proof=candidate_add,
        baseline_full_multiplier_phase_proof=baseline_proof,
        candidate_full_multiplier_phase_proof=candidate_proof,
        actual_source_bypasses=bypasses,
        removed_source_cx=old["baseline"]["source"]["cx"]-now["cx"],
        elligible_only_when_public_constant_low_half=True,
        both_circuits_32_logical_qubits=True,both_circuits_25_clean_helpers=True,
        every_emitted_gate_output_complex_amplitude_plus_one=True)
    return dict(baseline=baseline_qc,candidate=candidate_qc),proof


def cpu_compile(pm,qc):
    st=time.perf_counter()
    result=pm.run(qc)
    elapsed=time.perf_counter()-st
    ops={str(k):int(v) for k,v in result.count_ops().items()}
    cz=ops.get("cz",0)
    depth=result.depth()
    if not (cz>0 and depth>0 and result.num_qubits>=qc.num_qubits):
        raise AssertionError("Invalid CPU ISA compiler result")
    return dict(cz=int(cz),depth=int(depth),
        native_count_ops=ops,device_width=int(result.num_qubits),
        native_size=int(result.size()),compiler_seconds=elapsed)


def signed_summary(rows):
    assert len(rows)==len(SEEDS)
    ds=[row["delta_candidate_minus_baseline"] for row in rows]
    czs=[d["cz"] for d in ds]
    depths=[d["depth"] for d in ds]
    wins=sum(x<0 and y<0 for x,y in zip(czs,depths))
    med_cz=statistics.median(czs)
    med_depth=statistics.median(depths)
    return dict(paired_seeds=8,
       strict_both_resource_wins=wins,
       strictly_less_cz_seeds=sum(x<0 for x in czs),
       strictly_less_depth_seeds=sum(x<0 for x in depths),
       median_paired_cz_delta=med_cz,
       median_paired_depth_delta=med_depth,
       minimum_paired_cz_delta=min(czs),
       maximum_paired_cz_delta=max(czs),
       minimum_paired_depth_delta=min(depths),
       maximum_paired_depth_delta=max(depths),
       six_of_eight_both_resources_rule=(wins>=6),
       median_both_resources_negative=(med_cz<0 and med_depth<0),
       complete_fixed_seed_list=True)


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f"qrr_n35_one_bit_carry_bypass_base{base}.json"
    receipt=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        created_utc=datetime.now(timezone.utc).isoformat(),
        preregistration="docs/QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_PREREG.md",
        N=N,base=base,experiment="public one-bit constant-adder carry simplification vs robust De Morgan comparator",
        seeds=list(SEEDS),optimization_level=1,read_only_native_target="ibm_fez",
        historical_anchor=HISTORICAL[base],
        original_de_morgan_and_carry_semantics_preserved=True,
        only_one_constant_adder_change=True,
        source_order_not_injected=True,private_factors_not_used=True,orbit_not_hardcoded=True,
        hardware_cz_limit=800,hardware_depth_limit=2000,
        qpu_jobs_submitted=0,quantum_runtime_used=False,paid_runtime_used=False,
        eight_pairs=[],status="STARTED",success=False)
    def save():path.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        circuits,proof=prove_source_variants_before_target(base)
        receipt["exact_source_complex_proofs"]=proof
        receipt["status"]="SOURCE_COMPLEX_GATE_PROOFS_PASSED_BEFORE_BACKEND"
        save()
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Fez target backend missing/wrong device width")
        receipt["fez_target_device_qubits"]=int(backend.num_qubits)
        receipt["status"]="EIGHT_MATCHED_SEED_CPU_COMPILATIONS"
        save()

        for seed in SEEDS:
            pm=generate_preset_pass_manager(
                backend=backend,optimization_level=1,seed_transpiler=seed)
            old=cpu_compile(pm,circuits["baseline"])
            new=cpu_compile(pm,circuits["candidate"])
            delta=dict(cz=new["cz"]-old["cz"],depth=new["depth"]-old["depth"])
            row=dict(seed=seed,baseline=old,candidate=new,
                delta_candidate_minus_baseline=delta,
                strict_both_metric_improvement=(delta["cz"]<0 and delta["depth"]<0),
                baseline_hardware_feasible=(old["cz"]<=800 and old["depth"]<=2000),
                candidate_hardware_feasible=(new["cz"]<=800 and new["depth"]<=2000))
            receipt["eight_pairs"].append(row)
            save()
            print("FIXED MATCHED N35 CARRY BYPASS CPU",base,seed,
                "BASELINE",old["cz"],old["depth"],
                "CANDIDATE",new["cz"],new["depth"],
                "DELTA",delta["cz"],delta["depth"],
                "JOINT",row["strict_both_metric_improvement"],
                "HARDWARE",row["candidate_hardware_feasible"],
                "NO QPU",flush=True)

        summ=signed_summary(receipt["eight_pairs"])
        anchor=next(row for row in receipt["eight_pairs"] if row["seed"]==8776)
        historical=HISTORICAL[base]["baseline"]
        anchor_ok=(anchor["baseline"]["cz"]==historical["cz"]
                   and anchor["baseline"]["depth"]==historical["depth"])
        summ["seed8776_baseline_historical_exact_reproduction"]=anchor_ok
        summ["robust_engineering_per_base_pass"]=bool(
             anchor_ok and summ["six_of_eight_both_resources_rule"] and
             summ["median_both_resources_negative"])
        summ["all_original_and_new_seeds_fail_device_heuristic"]=all(
            not row["baseline_hardware_feasible"] and not row["candidate_hardware_feasible"]
            for row in receipt["eight_pairs"])
        receipt.update(status="COMPILE_SUCCESS",success=True,summary=summ,
            all_native_pair_compilations_completed=True,
            no_qpu_submissions=True)
        save()
        print("N35 ONE BIT CARRY BYPASS FINAL",base,json.dumps(summ,sort_keys=True),
              "ZERO QPU",flush=True)
        return 0
    except Exception as exc:
        receipt.update(status="FAIL",success=False,
           exception_type=type(exc).__name__,exception_message=str(exc)[:1400],
           exception_traceback=traceback.format_exc()[-2700:],
           qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print("N35 ONE BIT CARRY BYPASS FAIL",base,type(exc).__name__,
              str(exc)[:800],traceback.format_exc()[-1400:],
              "ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(parser.parse_args().base))
