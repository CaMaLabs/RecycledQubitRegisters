#!/usr/bin/env python3
"""Frozen public constant complement-conjugation lowering, matched N35 seeds.

Chase Lunsford / CaMaLabs; ZERO QPU.
Only mod-64 inner +v adder lowering can change. For C(x)=63-x,
  C( C(x) - v (mod64) ) == x+v (mod64).
Both are phase-exact monomial X/CX/CCX/RCCX circuits. Choose an inner
encoding solely via frozen S=CX+6*CCX+3*RCCX public v source counts, before
backend access. Retain previously VERIFIED modulo35 per-k positive/signed
selection for both public bases; no factoring-order or orbit shortcuts.
Run exact complex amplitude source proofs BEFORE CPU Fez-target transpilation.
"""
from __future__ import annotations
import argparse,json,os,statistics,time,traceback
from datetime import datetime,timezone
from pathlib import Path

from qiskit import QuantumCircuit,QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_static_gate_cost_sign_selector as oldselector

old=oldselector.old
primitive=oldselector.primitive
best=oldselector.best
previous=oldselector.previous

BITS=6
N=35
BASES=(2,8)
SEEDS=(43,127,211,887,1597,3571,8017,25013)
ANCHOR=8776
REV="qrr-n35-complement-conjugated-public-constant-selector-v1-20261019"
ROOT=Path("results/ibm_shor35_complement_constant_selector")
OLD_ROOT=Path("results/ibm_shor35_static_gate_sign_selector")
ORIGINAL_INNER_ADD=old.one_bit_bypass_constant_add
INNER_SELECTION={}
DIRECT_CALLS=0
CONJUGATE_CALLS=0

FROZEN_BASELINE={
    2:dict(cz=6871,depth=16626,source=dict(cx=275,rccx=520,x=1508,ccx=148)),
    8:dict(cz=7315,depth=16286,source=dict(cx=284,rccx=538,x=1528,ccx=151)),
}


def original_previous_receipt(base):
    path=OLD_ROOT/f"qrr_n35_static_sign_selector_base{base}.json"
    result=json.loads(path.read_text())
    assert result["status"]=="COMPILE_SUCCESS" and result["success"]
    assert result["summary"]["robust_gate_per_base_pass"]
    assert result["summary"]["original_8776_anchor_exact"]
    return result


def direct_constant_add(qc,target,value,controls,carry,chain):
    return ORIGINAL_INNER_ADD(qc,target,value,controls,carry,chain)


def conjugated_constant_add(qc,target,value,controls,carry,chain):
    """No gadget assumptions; literal Qiskit X^6 ADD(-v) X^6.

    Operates even if source enable is false, in which case two X layers
    cancel exactly, including their complex phase.
    """
    bits=list(target)
    assert len(bits)==BITS
    for bit in bits:
        qc.x(bit)
    ORIGINAL_INNER_ADD(qc,bits,-int(value),controls,carry,chain)
    for bit in reversed(bits):
        qc.x(bit)


def public_inner_add_source(v,method):
    enable=QuantumRegister(1,"enable")
    work=QuantumRegister(BITS,"work")
    carry=QuantumRegister(BITS,"carry")
    scratch=QuantumRegister(BITS+3,"scratch")
    qc=QuantumCircuit(enable,work,carry,scratch)
    adder=direct_constant_add if method=="direct" else conjugated_constant_add
    adder(qc,work,v,[enable[0]],carry,scratch)
    return qc,dict(enable=list(enable),work=list(work),
                   carry=list(carry),scratch=list(scratch))


def select_inner_source_before_backend():
    """All public values v in [0,63]; same k-free map for BOTH full bases."""
    choices={}
    score_rows=[]
    source={}
    for v in range(1<<BITS):
        direct,dr=public_inner_add_source(v,"direct")
        conj,cr=public_inner_add_source(v,"conjugated")
        dc={str(x):int(n) for x,n in direct.count_ops().items()}
        cc={str(x):int(n) for x,n in conj.count_ops().items()}
        ds=oldselector.source_gate_cost(dc)
        cs=oldselector.source_gate_cost(cc)
        chosen=("conjugated" if v and cs<ds else "direct")
        source[v]=dict(direct=(direct,dr),conjugated=(conj,cr))
        choices[v]=chosen
        score_rows.append(dict(public_value=v,direct_source_gate_ops=dc,
            conjugated_source_gate_ops=cc,direct_source_score=ds,
            conjugated_source_score=cs,selected_source_encoding=chosen,
            conjugated_strictly_cheaper_source_proxy=(cs<ds)))
    assert len(choices)==64 and choices[0]=="direct"
    assert all(choices[v]==("conjugated" if v and
             score_rows[v]["conjugated_source_score"]<
             score_rows[v]["direct_source_score"] else "direct") for v in choices)
    return choices,score_rows,source


def exact_inner_phase_gate_proof(source):
    cases=0
    details=[]
    for v in range(64):
        for method in ("direct","conjugated"):
            qc,regs=source[v][method]
            ids,instructions,ops=previous.actual_complex_instructions(qc)
            cpos=ids[regs["enable"][0]]
            workpos=[ids[q] for q in regs["work"]]
            aux=[ids[q] for label in ("carry","scratch") for q in regs[label]]
            cnt=0
            for enabled in (0,1):
                for x in range(64):
                    state=enabled<<cpos
                    for j,p in enumerate(workpos):
                        state|=((x>>j)&1)<<p
                    out,amplitude=previous.evolve_basis(instructions,state)
                    actual=sum(((out>>p)&1)<<j for j,p in enumerate(workpos))
                    wanted=(x+v)%64 if enabled else x
                    if actual!=wanted or ((out>>cpos)&1)!=enabled:
                        raise AssertionError(json.dumps(dict(
                            stage="inner add",method=method,value=v,
                            enabled=enabled,x=x,actual=actual,wanted=wanted)))
                    if any((out>>p)&1 for p in aux):
                        raise AssertionError(
                            f"Dirty inner carry/scratch v={v} method={method} x={x}")
                    previous.check_exact_phase(amplitude,
                        f"inner value={v} method={method} enabled={enabled} x={x}")
                    cases+=1
                    cnt+=1
            assert cnt==128
            details.append(dict(public_value=v,method=method,
                 actual_emitted_complex_cases=cnt,source_ops=ops,
                 output_phase_exact_plus_one=True,all_helpers_clean=True))
    assert cases==16384 and len(details)==128
    return dict(pass_all=True,actual_operator_basis_cases=cases,
        all_64_public_mod64_values=True,both_methods_direct_and_conjugated=True,
        both_enable_values=True,all_64_work_values=True,
        all_carry_scratch_clean=True,output_phase_exact_plus_one=True,
        per_value_method_details=details)


def patched_source_add(qc,target,value,controls,carry,chain):
    """One frozen public mod64 value dispatch, independent of base or native ISA."""
    global DIRECT_CALLS,CONJUGATE_CALLS
    v=int(value)%64
    choice=INNER_SELECTION.get(v)
    if choice=="conjugated":
        CONJUGATE_CALLS+=1
        return conjugated_constant_add(qc,target,value,controls,carry,chain)
    if choice=="direct":
        DIRECT_CALLS+=1
        return direct_constant_add(qc,target,value,controls,carry,chain)
    raise AssertionError(f"Missing public inner mod64 source selection for {v}")


def verify_and_build_base(base,prior):
    """Entire source fixed and phase-proved BEFORE backend is read."""
    global INNER_SELECTION,DIRECT_CALLS,CONJUGATE_CALLS

    # Clear every global monkey patch from previous experiments, as the
    # original static sign-selector script explicitly intended.
    oldselector.bootstrap_original_best()
    assert old.one_bit_bypass_constant_add is ORIGINAL_INNER_ADD

    # Original public k selector (sign correction) MUST match archived source
    # decision/score rows, not be recomputed from the NEW adder scores.
    kmap,krows,positives,signeds=oldselector.prebackend_static_source_selector()
    assert krows==prior["prebackend_public_k_source_score_table"]
    assert {str(k):kmap[k] for k in sorted(kmap)}==prior["public_k_sign_selection"]
    assert all(kmap[k]==("signed" if k%2 else "positive") for k in range(1,N))

    inner_map,inner_rows,source=select_inner_source_before_backend()
    inner_phase=exact_inner_phase_gate_proof(source)
    assert inner_phase["pass_all"] and inner_phase["actual_operator_basis_cases"]==16384

    old_identity=oldselector.standalone_public_arithmetic_identity()
    assert old_identity["pass_all"] and old_identity["cases"]==3366
    old_comparator=oldselector.dm.exhaustive_demorgan_comparator_phase_proof()
    assert old_comparator["pass_all"] and old_comparator["actual_emitted_gate_cases"]==42672
    assert old_comparator["final_complex_phase_plus_one_every_case"]
    # First rerun independently all ORIGINAL positive and signed modadd phases.
    original_modadd=oldselector.quantum_phase_per_k_adds(positives,signeds)
    assert original_modadd["pass_all"] and original_modadd["total_quantum_operator_basis_cases"]==6732

    # Reconstruct the audited ORIGINAL selected source, and match its gate
    # distribution to its original unaltered repository JSON.
    _,original_selected,old_proof=oldselector.prove_whole_source_variants(base,kmap)
    frozen_proof=prior["prebackend_exact_quantum_gate_proofs"]["whole_full_multiplier"]
    for name in ("original_full","candidate_full"):
        assert old_proof[name]["quantum_source_gate_counts"]==frozen_proof[name]["quantum_source_gate_counts"]
    assert old_proof["selection_for_each_weight"]==frozen_proof["selection_for_each_weight"]
    assert old_proof["candidate_full"]["quantum_source_gate_counts"]==FROZEN_BASELINE[base]["source"]

    # ONE changed component: all original inner 64-value adds now choose
    # between direct and complement-conjugated, based on public source S.
    INNER_SELECTION=dict(inner_map)
    old.one_bit_bypass_constant_add=patched_source_add
    best.constant_add_from_prefix_carry=patched_source_add

    candidate_pos={}
    candidate_signed={}
    for k in range(1,N):
        candidate_pos[k]=oldselector.source_add_circuit(k,"positive")
        candidate_signed[k]=oldselector.source_add_circuit(k,"signed")
    candidate_modadd=oldselector.quantum_phase_per_k_adds(candidate_pos,candidate_signed)
    assert candidate_modadd["pass_all"] and candidate_modadd["total_quantum_operator_basis_cases"]==6732
    assert candidate_modadd["exact_complex_phase_plus_one"]

    DIRECT_CALLS=0
    CONJUGATE_CALLS=0
    oldselector.SELECTION=dict(kmap)
    oldselector.SIGNED_CALLS=0
    oldselector.POSITIVE_CALLS=0
    primitive.modadd=oldselector.structural_selected_modadd
    best.optimized_modadd=oldselector.structural_selected_modadd
    candidate,cregs=previous.verified.build(base)
    observed_direct=DIRECT_CALLS
    observed_conjugated=CONJUGATE_CALLS
    new_full=previous.exhaustive_full_multiplier_phases(candidate,cregs,base)
    assert new_full["pass_all"] and new_full["full_residue_control_basis_cases"]==128
    assert new_full["all_25_auxiliaries_clean"] and new_full["exact_complex_output_phase_plus_one"]
    assert old_proof["candidate_full"]["pass_all"] and old_proof["candidate_full"]["all_25_auxiliaries_clean"]
    assert original_selected.num_qubits==candidate.num_qubits==32
    expected_signed=sum(kmap[k]=="signed" for k in oldselector.public_weighted_constants(base))
    assert oldselector.SIGNED_CALLS==expected_signed
    assert oldselector.SIGNED_CALLS+oldselector.POSITIVE_CALLS==12
    assert observed_direct+observed_conjugated>0
    candidate_source=new_full["quantum_source_gate_counts"]
    baseline_source=old_proof["candidate_full"]["quantum_source_gate_counts"]

    print("BEFORE BACKEND SOURCE EXACT QUANTUM PROOF base",base,
        "all v direct/conjugate",inner_phase["actual_operator_basis_cases"],
        "comparator",old_comparator["actual_emitted_gate_cases"],
        "old/candidate modulo35 each",original_modadd["total_quantum_operator_basis_cases"],
        candidate_modadd["total_quantum_operator_basis_cases"],
        "old/candidate full",old_proof["candidate_full"]["full_residue_control_basis_cases"],
        new_full["full_residue_control_basis_cases"],
        "selected complementary inner adds",observed_conjugated,
        "direct",observed_direct,
        "source old/new",baseline_source,candidate_source,
        "ALL complex amplitudes +1 25 clean NO QPU",flush=True)

    result=dict(pass_all=True,archived_public_k_sign_rows_exact_match=True,
        archived_public_k_sign_selection_exact_match=True,
        original_baseline_full_gate_counts_exact_match=True,
        public_64_value_source_score_table=inner_rows,
        inner_64_value_encoding_selector={str(k):inner_map[k] for k in sorted(inner_map)},
        selected_conjugate_values=[v for v in range(64) if inner_map[v]=="conjugated"],
        selected_conjugated_inner_addition_calls=observed_conjugated,
        selected_direct_inner_addition_calls=observed_direct,
        original_public_arithmetic_identities=old_identity,
        original_de_morgan_comparator_complex_proof=old_comparator,
        both_inner_mod64_adders_operator_proof=inner_phase,
        original_both_outer_signs_mod35_phase_proof=original_modadd,
        candidate_both_outer_signs_mod35_phase_proof=candidate_modadd,
        original_full_multiplier_phase_proof=old_proof["candidate_full"],
        candidate_full_multiplier_phase_proof=new_full,
        original_full_source_gates=baseline_source,
        candidate_full_source_gates=candidate_source,
        exact_final_complex_output_phase_plus_one=True,
        full_residue_y_zero_through_63=True,
        all_25_auxiliary_qubits_clean=True,both_source_width32=True)
    return original_selected,candidate,result


def summarize(rows,archived):
    fresh=[r for r in rows if r["seed"]!=ANCHOR]
    assert len(fresh)==8
    dz=[r["candidate_minus_prior_selected"]["cz"] for r in fresh]
    dd=[r["candidate_minus_prior_selected"]["depth"] for r in fresh]
    medz=statistics.median(dz)
    medd=statistics.median(dd)
    wins=sum(z<0 and d<0 for z,d in zip(dz,dd))
    a=next(r for r in rows if r["seed"]==ANCHOR)
    old_anchor=next(r for r in archived["matched_seed_pairs"] if r["seed"]==ANCHOR)["candidate"]
    anchor_matches=a["prior_selected"]["cz"]==old_anchor["cz"] and a["prior_selected"]["depth"]==old_anchor["depth"]
    changes=rows[0]["source_conjugated_inner_adds"]>0
    return dict(eight_new_seed_pairs=len(fresh),all_nine_pairs_recorded=len(rows)==9,
      anchor_8776_checked_separately=True,
      frozen_8776_previous_selected_anchor_exact=anchor_matches,
      prior_target_comparability_inconclusive_if_anchor_drift=not anchor_matches,
      new_joint_CZ_and_depth_improvement_seed_count=wins,
      new_CZ_improvement_seeds=sum(z<0 for z in dz),
      new_depth_improvement_seeds=sum(d<0 for d in dd),
      median_new_paired_CZ_delta=medz,median_new_paired_depth_delta=medd,
      min_new_CZ_delta=min(dz),max_new_CZ_delta=max(dz),
      min_new_depth_delta=min(dd),max_new_depth_delta=max(dd),
      at_least_six_of_eight_joint_wins=(wins>=6),
      both_new_paired_medians_strictly_negative=(medz<0 and medd<0),
      nonzero_conjugated_inner_adds=changes,
      robust_engineering_per_base_pass=bool(
          anchor_matches and changes and wins>=6 and medz<0 and medd<0),
      all_nine_pairs_fail_hardware_gate=all(
          not r["prior_hardware_feasible"] and
          not r["candidate_hardware_feasible"] for r in rows))


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f"qrr_n35_complement_constant_selector_base{base}.json"
    rec=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
       utc=datetime.now(timezone.utc).isoformat(),
       preregistration="docs/QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_PREREG.md",
       experiment="source-only direct vs complement-conjugated inner mod64 adder selector, original 34-k sign map unchanged",
       base=base,N=N,seeds=[ANCHOR]+list(SEEDS),new_seeds=list(SEEDS),historical_anchor_seed=ANCHOR,
       original_inner_source_formula="cx+6*ccx+3*rccx; X excluded; ties original direct",
       original_outer_sign_map_immutable=True,
       read_only_ibm_target="ibm_fez",optimizer_level=1,
       hard_device_cz_limit=800,hard_device_depth_limit=2000,
       true_order_not_used=True,prime_factors_not_used=True,public_orbit_not_compiled=True,
       qpu_jobs_submitted=0,quantum_runtime_used=False,paid_runtime_used=False,
       paired_native_seed_results=[],status="STARTED",success=False)
    def save():
        path.write_text(json.dumps(rec,indent=2,default=str)+"\n")
    save()
    try:
        archived=original_previous_receipt(base)
        old_c,new_c,proof=verify_and_build_base(base,archived)
        rec["before_target_exact_complex_source_proofs"]=proof
        rec["status"]="SOURCE_COMPLEX_GATE_PROOF_PASSED"
        save()

        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        svc=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=svc.backend("ibm_fez")
        assert not getattr(backend,"simulator",False)
        assert backend.num_qubits>=32
        rec["fez_target_device_qubits"]=int(backend.num_qubits)
        rec["status"]="READ_ONLY_FEZ_CPU_NATIVE_COMPILATION"
        save()
        for seed in (ANCHOR,)+SEEDS:
            pm=generate_preset_pass_manager(backend=backend,
                optimization_level=1,seed_transpiler=seed)
            oldval=oldselector.native_compile(pm,old_c)
            newval=oldselector.native_compile(pm,new_c)
            delta=dict(cz=newval["cz"]-oldval["cz"],
                       depth=newval["depth"]-oldval["depth"])
            row=dict(seed=seed,prior_selected=oldval,candidate=newval,
                candidate_minus_prior_selected=delta,
                strict_both_native_resources_improve=(delta["cz"]<0 and delta["depth"]<0),
                source_conjugated_inner_adds=proof["selected_conjugated_inner_addition_calls"],
                prior_hardware_feasible=(oldval["cz"]<=800 and oldval["depth"]<=2000),
                candidate_hardware_feasible=(newval["cz"]<=800 and newval["depth"]<=2000))
            rec["paired_native_seed_results"].append(row)
            save()
            print("N35 CONJUGATE INNER SOURCE CPU",base,seed,
                "ANCHOR" if seed==ANCHOR else "NEW",
                "OLD",oldval["cz"],oldval["depth"],
                "NEW",newval["cz"],newval["depth"],
                "DELTA",delta["cz"],delta["depth"],
                "JOINT",row["strict_both_native_resources_improve"],
                "HARDWARE",row["candidate_hardware_feasible"],
                "NO QPU",flush=True)
        summary=summarize(rec["paired_native_seed_results"],archived)
        rec.update(status="COMPILE_SUCCESS",success=True,
            new_seed_summary=summary,
            all_36_native_cpu_compilations_completed=True,
            no_actual_quantum_device_use=True)
        save()
        print("N35 COMPLEMENT CONJUGATE SELECTOR FINAL",base,
            json.dumps(summary,sort_keys=True),"NO QPU",flush=True)
        return 0
    except Exception as exc:
        rec.update(status="FAIL",success=False,
            failure_type=type(exc).__name__,
            failure_message=str(exc)[:1700],
            failure_traceback=traceback.format_exc()[-3200:],
            qpu_jobs_submitted=0,quantum_runtime_used=False,paid_runtime_used=False)
        save()
        print("N35 COMPLEMENT CONJUGATE FAIL",base,type(exc).__name__,
            str(exc)[:900],traceback.format_exc()[-1700:],
            "ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",type=int,choices=BASES,required=True)
    raise SystemExit(main(ap.parse_args().base))
