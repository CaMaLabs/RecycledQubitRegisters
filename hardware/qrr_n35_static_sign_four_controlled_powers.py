#!/usr/bin/env python3
"""Four-control public N35 modular-power BLOCK, old vs proven static sign rule.

Research lead Chase Lunsford / CaMaLabs. Distinct from full Shor: NO QFT,
inverse QFT, phase feedback, measurement or quantum device execution.
Phase input 4 + work 6 + 25 CLEAN helper qubits = 35 logical qubits.
Every source gate interpreted with its TRUE complex Qiskit Operator, with
1024 four-control/residue basis states per version (positive/selected).
Preregistered 8 NEW paired native compiler seeds to read-only IBM Fez target.
"""
from __future__ import annotations
import argparse,json,os,time,statistics,traceback
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit, QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_static_gate_cost_sign_selector as oldsel

N=35
BITS=6
PHASE_BITS=4
BASES=(2,8)
SEEDS=(239,647,1453,3701,6211,9421,16673,27191)
ANCHOR=8776
REV="qrr-n35-four-public-powers-static-sign-source-20261020-v1"
ROOT=Path("results/ibm_shor35_four_power_sign_selector")
BASELINE_ARCHIVED="results/ibm_shor35_static_gate_sign_selector"
FROZEN_HIST={
  2:dict(original=(7887,18221),selected=(6871,16626)),
  8:dict(original=(7802,18449),selected=(7315,16286))
}


def archived_original(base):
    f=Path(BASELINE_ARCHIVED)/f"qrr_n35_static_sign_selector_base{base}.json"
    d=json.loads(f.read_text())
    assert d["status"]=="COMPILE_SUCCESS" and d["success"]
    assert d["summary"]["robust_gate_per_base_pass"]
    return d


def phase_source_preflight(base,archived):
    """Prior 34 public sign-rule source decisions/ideal quantum phases intact."""
    oldsel.bootstrap_original_best()
    algebra=oldsel.standalone_public_arithmetic_identity()
    inverse=oldsel.dm.boolean_and_inverse_operator_proof()
    comparator=oldsel.dm.exhaustive_demorgan_comparator_phase_proof()
    mapping,source_rows,positive,signed=oldsel.prebackend_static_source_selector()
    assert source_rows==archived["prebackend_public_k_source_score_table"]
    assert {str(k):mapping[k] for k in sorted(mapping)}==archived["public_k_sign_selection"]
    assert all(mapping[k]==("signed" if k%2 else "positive")
               for k in range(1,N))
    assert algebra["pass_all"] and algebra["cases"]==3366
    assert comparator["pass_all"] and comparator["actual_emitted_gate_cases"]==42672
    per_k=oldsel.quantum_phase_per_k_adds(positive,signed)
    assert per_k["pass_all"] and per_k["total_quantum_operator_basis_cases"]==6732
    orig1,selected1,one_proof=oldsel.prove_whole_source_variants(base,mapping)
    frozen=archived["prebackend_exact_quantum_gate_proofs"]["whole_full_multiplier"]
    for label in ("original_full","candidate_full"):
        proof=one_proof[label]
        assert proof["pass_all"] and proof["exact_complex_output_phase_plus_one"]
        assert proof["all_25_auxiliaries_clean"]
        assert proof["quantum_source_gate_counts"]==frozen[label]["quantum_source_gate_counts"]
    assert orig1.num_qubits==selected1.num_qubits==32
    print("PHASE SOURCE AND ORIGINAL 34 PUBLIC SIGN CHOICES EXACT",base,
          "3366 public identities, 42672 comparator, 6732 per-k gates,",
          "128+128 old vs selected ONE-multiplier +1 complex phase",flush=True)
    return mapping,(orig1,selected1),dict(
        public_arithmetic_identity=algebra,
        rccx_inverse_operator_identity=inverse,
        comparator_exact_complex_phase=comparator,
        both_signed_positive_k_1_to_34_exact_complex_phase=per_k,
        original_single_multiplier_complex_phase=one_proof,
        frozen_original_34_source_gate_vectors_exact_match=True,
        frozen_original_34_sign_choices_exact_match=True,
        original_single_multiplier_source_exact_match=True,
        original_single_multiplier_source_qubits=32,
        all_proofs_pass_before_any_IBM_backend_access=True)


def public_schedule(base):
    schedule=[pow(base,1<<i,N) for i in range(PHASE_BITS)]
    assert schedule==({2:[2,4,16,11],8:[8,29,1,1]}[base])
    return schedule


def build_four_controlled_powers(base,variant,mapping):
    """Same clean arithmetic, controlled in-place multiplications on shared 6-bit register.

    No QFT or order arithmetic. Only skip a public m_j == 1 identity power.
    The invalid-state validity latch covers all four stages and is uncomputed.
    """
    assert base in BASES and variant in ("original","selected")
    oldsel.bootstrap_original_best()
    if variant=="original":
        oldsel.primitive.modadd=oldsel.POSITIVE_MODADD
        oldsel.best.optimized_modadd=oldsel.POSITIVE_MODADD
    else:
        oldsel.SELECTION=dict(mapping)
        oldsel.SIGNED_CALLS=0
        oldsel.POSITIVE_CALLS=0
        oldsel.primitive.modadd=oldsel.structural_selected_modadd
        oldsel.best.optimized_modadd=oldsel.structural_selected_modadd

    phase=QuantumRegister(PHASE_BITS,"phase")
    work=QuantumRegister(BITS,"work")
    acc=QuantumRegister(BITS,"acc")
    wrap=QuantumRegister(1,"wrap")
    valid=QuantumRegister(1,"valid")
    carry=QuantumRegister(BITS,"carry")
    scratch=QuantumRegister(BITS+3,"scratch")
    active=QuantumRegister(1,"active")
    enable=QuantumRegister(1,"enable")
    qc=QuantumCircuit(phase,work,acc,wrap,valid,carry,scratch,active,enable,
        name=f"N35_four_controlled_powers_{variant}_base{base}")
    schedule=public_schedule(base)
    counters=[]
    # Previously source-verified public work<35 comparator, computed ONCE.
    oldsel.primitive.predicate(qc,work,N,valid[0],carry,scratch,geq=False)
    for stage,m in enumerate(schedule):
        if m==1:
            counters.append(dict(stage=stage,public_multiplier=m,
                                 identity_round_skipped=True,weighted_additions=0))
            continue
        inv=pow(m,-1,N)  # public multiplicative inverse; no factors/order.
        qc.ccx(phase[stage],valid[0],active[0])
        for i in range(BITS):
            qc.ccx(active[0],work[i],enable[0])
            oldsel.primitive.modadd(qc,acc,m*(1<<i),N,
                                   [enable[0]],wrap[0],carry,scratch)
            qc.ccx(active[0],work[i],enable[0])
        for a,b in zip(work,acc):
            oldsel.primitive.controlled_swap(qc,a,b,[active[0]],scratch)
        for i in range(BITS):
            qc.ccx(active[0],work[i],enable[0])
            oldsel.primitive.modadd(qc,acc,-inv*(1<<i),N,
                                   [enable[0]],wrap[0],carry,scratch)
            qc.ccx(active[0],work[i],enable[0])
        qc.ccx(phase[stage],valid[0],active[0])
        counters.append(dict(stage=stage,public_multiplier=m,
                             identity_round_skipped=False,weighted_additions=12))
    oldsel.primitive.predicate(qc,work,N,valid[0],carry,scratch,geq=False)

    regs=dict(phase=list(phase),work=list(work),acc=list(acc),
              wrap=list(wrap),valid=list(valid),carry=list(carry),
              scratch=list(scratch),active=list(active),enable=list(enable))
    nonid=sum(m!=1 for m in schedule)
    if variant=="selected":
        assert oldsel.SIGNED_CALLS+oldsel.POSITIVE_CALLS==12*nonid
        counters.append(dict(total_signed_k_calls=oldsel.SIGNED_CALLS,
                             total_positive_k_calls=oldsel.POSITIVE_CALLS))
    assert qc.num_qubits==35
    return qc,regs,counters


def exhaustive_four_controlled_power_phase(qc,regs,base):
    """TRUE emitted source phase+1 and 25 clean aux over 16*64=1024 inputs."""
    idx, instructions, gate_counts=oldsel.previous.actual_complex_instructions(qc)
    phase_positions=[idx[q] for q in regs["phase"]]
    work_positions=[idx[q] for q in regs["work"]]
    aux=[idx[q] for name in ("acc","wrap","valid","carry","scratch","active","enable")
         for q in regs[name]]
    assert len(phase_positions)==4 and len(work_positions)==6 and len(aux)==25
    assert set(aux).isdisjoint(set(phase_positions)|set(work_positions))
    assert set(gate_counts).issubset({"x","cx","ccx","rccx"})
    checked=0
    for control in range(16):
        for y in range(64):
            state=0
            for i,p in enumerate(phase_positions):
                state|=((control>>i)&1)<<p
            for i,p in enumerate(work_positions):
                state|=((y>>i)&1)<<p
            out,amp=oldsel.previous.evolve_basis(instructions,state)
            got_phase=sum(((out>>p)&1)<<i for i,p in enumerate(phase_positions))
            got_work=sum(((out>>p)&1)<<i for i,p in enumerate(work_positions))
            expected=(y*pow(base,control,N))%N if y<N else y
            if got_phase!=control or got_work!=expected:
                raise AssertionError(json.dumps(dict(stage="four_controlled_powers",
                   base=base,control=control,initial=y,
                   phase_out=got_phase,work_out=got_work,want=expected)))
            if any((out>>p)&1 for p in aux):
                raise AssertionError(json.dumps(dict(
                   stage="four_power_dirty_aux",base=base,control=control,y=y)))
            oldsel.previous.check_exact_phase(amp,
                f"four phase power base={base} control={control} y={y}")
            checked+=1
    assert checked==1024
    return dict(pass_all=True,exact_source_operator_basis_cases=checked,
        all_16_phase_control_patterns=True,
        all_64_sixbit_residues=True,
        invalid_work_inputs_identity=True,all_25_helpers_clean=True,
        phase_inputs_unchanged=True,exact_complex_phase_plus_one=True,
        source_gate_histogram=gate_counts,source_instruction_count=len(instructions),
        source_logical_qubits=qc.num_qubits)


def cpu_compile(pm,qc):
    start=time.perf_counter()
    native=pm.run(qc)
    ops={str(k):int(v) for k,v in native.count_ops().items()}
    cz=ops.get("cz",0);depth=native.depth()
    assert cz>0 and depth>0 and native.num_qubits>=35
    return dict(native_cz=cz,native_depth=depth,
                native_ops=ops,
                device_width=int(native.num_qubits),
                native_total_ops=int(native.size()),
                compiler_seconds=time.perf_counter()-start)


def compile_summary(pairs,anchor_matches):
    dz=[p["paired_delta"]["cz"] for p in pairs]
    dd=[p["paired_delta"]["depth"] for p in pairs]
    wins=sum(z<0 and d<0 for z,d in zip(dz,dd))
    medz=statistics.median(dz);medd=statistics.median(dd)
    return dict(paired_seed_count=len(pairs),
       strict_both_metrics_wins=wins,
       strict_cz_wins=sum(z<0 for z in dz),
       strict_depth_wins=sum(d<0 for d in dd),
       paired_median_cz_delta=medz,
       paired_median_depth_delta=medd,
       paired_min_cz_delta=min(dz),paired_max_cz_delta=max(dz),
       paired_min_depth_delta=min(dd),paired_max_depth_delta=max(dd),
       no_seed_excluded=True,
       frozen_single_stage_8776_anchors_reproduce=anchor_matches,
       meets_at_least_six_of_eight_joint_wins=(wins>=6),
       both_paired_medians_negative=(medz<0 and medd<0),
       robust_per_base_pass=bool(anchor_matches and wins>=6 and medz<0 and medd<0),
       historic_comparability_inconclusive=not anchor_matches,
       every_original_and_selected_block_fails_device_feasibility=all(
           not p["original_device_feasible"] and
           not p["selected_device_feasible"] for p in pairs))


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    output=ROOT/f"qrr_n35_four_power_sign_source_base{base}.json"
    receipt=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
       timestamp_utc=datetime.now(timezone.utc).isoformat(),
       preregistration="docs/QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_PREREG.md",
       public_N=N,public_base=base,public_power_schedule=public_schedule(base),
       phase_control_qubits=4,work_qubits=6,clean_auxiliary_qubits=25,
       total_source_logical_qubits=35,
       eight_NEW_seeds=list(SEEDS),single_stage_anchor_seed=8776,
       experiment_type="four public controlled modular-power UNITARY BLOCK, not full inverse-QFT Shor",
       backend_name="ibm_fez",optimization_level=1,
       physical_native_cz_cutoff=800,physical_native_depth_cutoff=2000,
       order_not_injected=True,factors_not_used=True,
       multiplicative_orbit_not_hardcoded=True,
       no_qft_or_measurement_or_quantum_device_run=True,
       qpu_jobs_submitted=0,paid_quantum_runtime_used=False,free_quantum_runtime_used=False,
       eight_seed_native_pairs=[],status="STARTED",success=False)
    def save():output.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        archived=archived_original(base)
        mapping,single,proof=phase_source_preflight(base,archived)
        receipt["original_source_phase_preflight"]=proof
        qc_orig,reg_orig,rounds_orig=build_four_controlled_powers(base,"original",mapping)
        qc_sel,reg_sel,rounds_sel=build_four_controlled_powers(base,"selected",mapping)
        src_orig=exhaustive_four_controlled_power_phase(qc_orig,reg_orig,base)
        src_sel=exhaustive_four_controlled_power_phase(qc_sel,reg_sel,base)
        assert src_orig["pass_all"] and src_sel["pass_all"]
        assert src_orig["exact_source_operator_basis_cases"]==1024
        assert src_sel["exact_source_operator_basis_cases"]==1024
        assert src_orig["exact_complex_phase_plus_one"] and src_sel["exact_complex_phase_plus_one"]
        assert sum(not z["identity_round_skipped"] for z in rounds_orig[:4])==(
            4 if base==2 else 2)
        assert sum(z["weighted_additions"] for z in rounds_sel[:4])==(
            48 if base==2 else 24)
        assert src_orig["source_gate_histogram"]!=src_sel["source_gate_histogram"],(
           "Static source sign selector was never exercised")
        receipt["four_power_source_phase_proofs"]=dict(
            original=src_orig,selected=src_sel,
            source_rounds_original=rounds_orig,source_rounds_selected=rounds_sel,
            public_identity_rounds=sum(m==1 for m in public_schedule(base)),
            source_gate_histograms_differ=True,
            two_source_blocks_1024_cases_each_pass=True)
        receipt["status"]="SOURCE_PHASE_VALIDATED_PRE_BACKEND"
        save()
        print("FOUR-CONTROL BLOCK EMITTED SOURCE COMPLEX PHASE PROOF PASS",base,
              "1024 original +1024 selected, 25 ancillas zero,",
              "control powers",public_schedule(base),
              "source original",src_orig["source_gate_histogram"],
              "selected",src_sel["source_gate_histogram"],flush=True)
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<35:
            raise AssertionError("Read-only hardware target too narrow or simulator")
        receipt["backend_target_qubits"]=int(backend.num_qubits)
        receipt["status"]="NATIVE_COMPILING_MATCHED"
        save()

        # Standalone historical anchor at SAME backend and Qiskit version,
        # separate from FRESH four-controlled-power comparisons.
        pass8776=generate_preset_pass_manager(
            backend=backend,optimization_level=1,seed_transpiler=ANCHOR)
        historical_old=cpu_compile(pass8776,single[0])
        historical_new=cpu_compile(pass8776,single[1])
        receipt["historical_one_multiplier_anchor"]=dict(
            seed=ANCHOR,original=historical_old,selected=historical_new)
        historic=FROZEN_HIST[base]
        anchor_matches=(historical_old["native_cz"],historical_old["native_depth"])==historic["original"] and (
              historical_new["native_cz"],historical_new["native_depth"])==historic["selected"]
        receipt["historical_one_multiplier_anchor"]["exact_reproduction"]=anchor_matches
        save()
        print("FROZEN ONE-MULTIPLIER 8776 ANCHOR",base,
              "original",historical_old["native_cz"],historical_old["native_depth"],
              "selected",historical_new["native_cz"],historical_new["native_depth"],
              "matches",anchor_matches,flush=True)

        for seed in SEEDS:
            pm=generate_preset_pass_manager(
                backend=backend,optimization_level=1,seed_transpiler=seed)
            compiled_old=cpu_compile(pm,qc_orig)
            compiled_new=cpu_compile(pm,qc_sel)
            delta=dict(cz=compiled_new["native_cz"]-compiled_old["native_cz"],
                depth=compiled_new["native_depth"]-compiled_old["native_depth"])
            row=dict(seed=seed,original=compiled_old,selected=compiled_new,
               paired_delta=delta,
               joint_two_metrics_strict_improvement=delta["cz"]<0 and delta["depth"]<0,
               original_device_feasible=(
                   compiled_old["native_cz"]<=800 and compiled_old["native_depth"]<=2000),
               selected_device_feasible=(
                   compiled_new["native_cz"]<=800 and compiled_new["native_depth"]<=2000))
            receipt["eight_seed_native_pairs"].append(row)
            save()
            print("FOUR-PHASE CPU NATIVE PAIR",base,seed,
                  "original CZ/depth",compiled_old["native_cz"],compiled_old["native_depth"],
                  "selected CZ/depth",compiled_new["native_cz"],compiled_new["native_depth"],
                  "delta",delta,
                  "both_win",row["joint_two_metrics_strict_improvement"],
                  "ZERO QPU",flush=True)

        summary=compile_summary(receipt["eight_seed_native_pairs"],anchor_matches)
        receipt.update(status="COMPILE_SUCCESS",success=True,all_eight_pairs_complete=True,
            summary=summary,qpu_jobs_submitted=0)
        save()
        print("FOUR-POWER N35 NATIVE CPU SUMMARY",base,json.dumps(summary,sort_keys=True),
             "NO QFT, ZERO QPU",flush=True)
        return 0
    except Exception as e:
        receipt.update(status="FAIL",success=False,
           failure_class=type(e).__name__,failure_message=str(e)[:2000],
           failure_trace=traceback.format_exc()[-3000:],
           qpu_jobs_submitted=0,paid_quantum_runtime_used=False,
           free_quantum_runtime_used=False)
        save()
        print("FOUR-POWER N35 ERROR",base,type(e).__name__,
           str(e)[:1200],traceback.format_exc()[-1800:],"ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(parser.parse_args().base))
