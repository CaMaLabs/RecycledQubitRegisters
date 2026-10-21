#!/usr/bin/env python3
"""Exact ideal N35 4bit wide IQFT readout outcome distribution, public factor tests.

Research lead: Chase Lunsford / CaMaLabs. No QPU, no IBM Quantum connection.
This is an ideal prediction for the already verified 35qubit 4-control QFT
circuit, NOT measurements, noise fidelity, recycled phase, or advantage.
Quantum source gate proofs and QFT matrix verified BEFORE distributions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
from math import gcd
import json
import traceback
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector

import qrr_n35_four_phase_iqft_readout_cpu as readout
import qrr_n35_static_sign_four_controlled_powers as powers

N=35
M=16
BASES=(2,8)
REV="qrr-n35-fourbit-ideal-iqft-factor-scoring-v1-20261020"
ROOT=Path("results/n35_ideal_iqft_outcome")
EPS=1e-9


def source_proof(base):
    """Repeat archived full 35q source gate basis proof; NEVER QPU/backend."""
    f=Path("results/ibm_shor35_four_phase_iqft_readout")/f"qrr_n35_four_phase_iqft_base{base}.json"
    historical=json.loads(f.read_text())
    assert historical["status"]=="COMPILE_SUCCESS" and historical["success"]
    assert historical["public_N"]==N and historical["public_base"]==base
    assert historical["source_all_phase_prechecks_completed"]
    iqft=readout.verify_inverse_fourier()
    archived=powers.archived_original(base)
    mapping,_,pre=powers.phase_source_preflight(base,archived)
    circuits={}
    proof={}
    structure={}
    for variant in ("original","selected"):
        power,regs,rounds=powers.build_four_controlled_powers(base,variant,mapping)
        p=powers.exhaustive_four_controlled_power_phase(power,regs,base)
        frozen=historical["prebackend_phase_proofs"][
            "old_source" if variant=="original" else "selected_source"]
        assert p["pass_all"] and p["exact_source_operator_basis_cases"]==1024
        assert p["all_25_helpers_clean"] and p["exact_complex_phase_plus_one"]
        assert p["source_gate_histogram"]==frozen["source_gate_histogram"]
        prior_receipt=json.loads(Path(historical["original_frozen_four_power_block_receipt"]).read_text())
        original_rounds_key="source_rounds_original" if variant=="original" else "source_rounds_selected"
        assert rounds==prior_receipt["four_power_source_phase_proofs"][original_rounds_key]
        assert [z["public_multiplier"] for z in rounds[:4]]==powers.public_schedule(base)
        readout_c,readout_check=readout.readout_circuit(power,regs,base,variant)
        assert readout_check["pass_all"]
        assert readout_check["exactly_four_terminal_measurements"]
        assert readout_check["four_H_initial_phase_preparations"]
        assert readout_c.num_qubits==35 and readout_c.num_clbits==4
        # No 2^35 state vector; exact prior 16*64 basis checks plus 16x16 QFT.
        proof[variant]=p
        structure[variant]=readout_check
        circuits[variant]=dict(readout_source_qubits=readout_c.num_qubits,
             readout_classical_bits=readout_c.num_clbits,
             original_power_source_size=int(power.size()),
             complete_readout_source_size=int(readout_c.size()))
    assert proof["original"]["source_logical_qubits"]==35
    assert proof["selected"]["source_logical_qubits"]==35
    return dict(pass_all=True,analytic_qft_unitary=iqft,
       prebackend_public_arithmetic=pre,
       full_power_source_proofs=proof,
       terminal_readout_checks=structure,
       source_circuit_sizes=circuits,
       full_source_1024_case_proof_per_variant=True,
       original_selected_identical_public_power_action=True,
       quantum_complex_output_phase_plus_one=True,
       all_25_ancillas_returned_zero=True)


def analytic_and_statevector_probabilities(base):
    """Exact (4 phase +6 work)-qubit image of known clean-aux 35q unitary."""
    qft=readout.verify_inverse_fourier()
    assert qft["pass_all"]
    powers_by_control=[pow(base,c,N) for c in range(M)]
    assert powers_by_control[0]==1
    # State order: bit [0:3] phase, bit [4:9] work.
    state=np.zeros((M*64,),dtype=complex)
    for c,y in enumerate(powers_by_control):
        state[c+M*y] += 1/4
    assert np.isclose(np.vdot(state,state).real,1,atol=1e-11)
    actual=np.asarray(
        Statevector(state).evolve(
            readout.QFTGate(4).inverse(),qargs=[0,1,2,3]
        ).data,dtype=complex)
    analytic=np.zeros_like(actual)
    for k in range(M):
        for c,y in enumerate(powers_by_control):
            analytic[k+M*y] += np.exp(-2j*np.pi*c*k/M)/M
    max_difference=float(np.max(np.abs(actual-analytic)))
    if max_difference>EPS:
        raise AssertionError(f"Full 1024 quantum complex output amplitudes disagree: {max_difference}")
    p_analytical=np.asarray([sum(abs(analytic[k+M*y])**2 for y in range(64))
                     for k in range(M)],dtype=float)
    p_state=np.asarray([sum(abs(actual[k+M*y])**2 for y in range(64))
                     for k in range(M)],dtype=float)
    if not np.all(np.isfinite(p_analytical)) or np.min(p_analytical)<-1e-11:
        raise AssertionError("Unphysical output distribution")
    if not np.allclose(p_analytical,p_state,rtol=0,atol=EPS):
        raise AssertionError("Trace-out work probabilities differ")
    if abs(sum(p_analytical)-1)>1e-10:
        raise AssertionError("Measurement probabilities not normalized")
    if any(y>=N for y in powers_by_control):
        raise AssertionError("Public modular work orbit outside valid residues")
    return list(p_analytical),dict(pass_all=True,
       independent_qiskit_statevector_amplitude_check=True,
       all_1024_complex_amplitudes_checked=True,
       max_complex_amplitude_difference=max_difference,
       distribution_normalized=True,
       total_probability=float(sum(p_analytical)),
       four_phase_bits=True,six_work_bits=True,
       trace_out_all_64_work_states=True,
       h4_prepared_phase_amplitude=0.25,
       public_power_work_values_for_16_controls=powers_by_control,
       original_and_selected_ideal_output_identical=True,
       quantum_device_measurements=0,
       proof_uses_no_private_factors_or_multiplicative_order=True)


def continued_fraction_denominators(k):
    """All exact regular CF convergents of PUBLIC rational k/16.

    Exclude q=1 (and k=0), retain only q=2..16, no label/period oracle.
    """
    if not 0<=k<M:
        raise ValueError("Measurement not four-bit")
    if k==0:
        return []
    n,d=k,M
    cf=[]
    while d:
        digit,remainder=divmod(n,d)
        cf.append(digit)
        n,d=d,remainder
    prevprev_num,prev_num=0,1
    prevprev_den,prev_den=1,0
    denoms=[]
    for coefficient in cf:
        num=coefficient*prev_num+prevprev_num
        den=coefficient*prev_den+prevprev_den
        if 2<=den<=M and den not in denoms:
            denoms.append(den)
        prevprev_num,prev_num=prev_num,num
        prevprev_den,prev_den=prev_den,den
    final=M//gcd(k,M)
    if final not in denoms:
        raise AssertionError(f"CF final rational denominator absent k={k} q={final}")
    return denoms


def factor_from_r(base,r):
    """Public modular exponent + ordinary two standard half-order gcds."""
    if r%2 or r<2:
        return None
    if pow(base,r,N)!=1:
        return None
    half=pow(base,r//2,N)
    gminus=gcd((half-1)%N,N)
    gplus=gcd((half+1)%N,N)
    factors=[g for g in (gminus,gplus) if 1<g<N and N%g==0]
    if factors:
        return dict(r=r,proper_factor=min(factors),
                    complementary_factor=N//min(factors),
                    public_half_power=half,
                    gcd_minus=gminus,gcd_plus=gplus)
    return None


def score_policy(base,k,limit_multiple):
    """NO factor, no order knowledge in candidate selection.

    For strict policy m=1 only; bounded policy m=1..4, r<=64.
    """
    assert limit_multiple in (1,4)
    denoms=continued_fraction_denominators(k)
    considered=[]
    seen=set()
    public_exponent_checks=0
    first_success=None
    for q in denoms:
        for multiplier in range(1,limit_multiple+1):
            r=q*multiplier
            if r>64 or r in seen:
                continue
            seen.add(r)
            is_even=(r%2==0)
            considered.append(dict(q=q,multiplier=multiplier,
                                   r=r,even=is_even))
            if not is_even:
                continue
            public_exponent_checks+=1
            witness=factor_from_r(base,r)
            if witness and first_success is None:
                first_success=dict(
                    continued_fraction_q=q,public_multiple=multiplier,
                    **witness)
    return dict(success=first_success is not None,
                first_success=first_success,
                continued_fraction_denominators=denoms,
                public_even_exponent_tests=public_exponent_checks,
                all_public_r_candidates=considered,
                input_measurement_zero_policy=(k==0 and not considered))


def public_classical_baseline(base):
    gminus=gcd(base-1,N)
    gplus=gcd(base+1,N)
    immediate=[x for x in (gminus,gplus) if 1<x<N and N%x==0]
    scan=[dict(candidate_even_r=r,result=factor_from_r(base,r))
          for r in (2,4,6,8)]
    return dict(
       gcd_base_minus_one=gminus,gcd_base_plus_one=gplus,
       pre_qft_immediate_factor=(min(immediate) if immediate else None),
       pre_qft_classical_gcd_preempts_quantum_claim=bool(immediate),
       four_public_even_exponent_scan=scan,
       classical_even_exponent_scan_finds_factor=any(x["result"] is not None
                         for x in scan),
       classical_inputs_only=True,
       no_period_or_factors_used_to_choose_exponent_candidates=True
    )


def descriptive_actual_order(base):
    """For POST-SCORING VALIDATION ONLY, not candidate generation."""
    hits=[r for r in range(1,71) if pow(base,r,N)==1]
    assert hits
    order=min(hits)
    expected=12 if base==2 else 4
    assert order==expected
    return dict(descriptive_only=True,actual_order=order,
       first_modulus_70_search=True,
       strictly_not_used_for_CF_candidate_generation_or_probabilities=True)


def run_base(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f"qrr_n35_ideal_iqft_outcomes_base{base}.json"
    receipt=dict(
      revision=REV,research_lead="Chase Lunsford / CaMaLabs",
      computed_utc=datetime.now(timezone.utc).isoformat(),
      preregistered_document="docs/QRR_N35_FOUR_BIT_IDEAL_OUTCOME_FACTOR_SCORING_PREREG.md",
      N=N,public_base=base,
      scope="ideal 4bit WIDE quantum phase readout with public CF proper factor tests",
      original_previous_readout_receipt=f"results/ibm_shor35_four_phase_iqft_readout/qrr_n35_four_phase_iqft_base{base}.json",
      source_phase_qubits=4,source_work_qubits=6,
      original_source_ancillas=25,
      external_qpu_calls=0,free_quantum_runtime_used=False,
      paid_quantum_runtime_used=False,
      no_IBM_backend_or_quantum_runtime_access=True,
      actual_quantum_device_shots=0,
      output_case_count=16,postprocessing_uses_true_order=False,
      success=False,status="STARTED"
    )
    def save():path.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        receipt["previous_source_exact_gate_verification"]=source_proof(base)
        receipt["status"]="FULL_35Q_SOURCE_AND_READOUT_REVERIFIED"
        save()
        print("N35 ORIGINAL+SELECTED POWER SOURCE 1024+1024 PASS",base,
            "ALL 25 CLEAN PHASE+1, 4 H, 16x16 IQFT, 4 MEASURE",flush=True)
        probabilities,ideal=analytic_and_statevector_probabilities(base)
        receipt["independent_analytic_statevector_check"]=ideal
        rows=[]
        for k,p in enumerate(probabilities):
            strict=score_policy(base,k,1)
            bounded=score_policy(base,k,4)
            assert not (k==0 and (strict["success"] or bounded["success"]))
            assert not(strict["success"] and not bounded["success"])
            rows.append(dict(phase_outcome_k=k,phase_fraction=f"{k}/16",
                ideal_probability=float(p),
                strict_CF_convergents=strict,
                bounded_public_multiples_upto_four=bounded))
        assert len(rows)==16
        weights=np.asarray(probabilities)
        strict_hit=np.asarray([int(x["strict_CF_convergents"]["success"]) for x in rows])
        bounded_hit=np.asarray([int(x["bounded_public_multiples_upto_four"]["success"])
                                for x in rows])
        score=dict(
          strict_cf_ideal_success_probability=float(np.dot(weights,strict_hit)),
          bounded_4_public_multiples_ideal_success_probability=float(np.dot(weights,bounded_hit)),
          strict_cf_uniform_fourbit_k_baseline=float(np.mean(strict_hit)),
          bounded_cf_uniform_fourbit_k_baseline=float(np.mean(bounded_hit)),
          all_16_outcomes_scored_without_postselection=True,
          phase_outcome_zero_never_scores_success=True,
          postprocessor_uses_true_period=False,
          bounded_4_public_modular_exponent_search_not_strict_shor=True,
          strict_successful_outcomes=[x["phase_outcome_k"] for x in rows
                                      if x["strict_CF_convergents"]["success"]],
          bounded_successful_outcomes=[x["phase_outcome_k"] for x in rows
                                      if x["bounded_public_multiples_upto_four"]["success"]]
        )
        baseline=public_classical_baseline(base)
        # IMPORTANT: order test is only a descriptive check after scoring.
        order=descriptive_actual_order(base)
        receipt.update(
          status="ALL_IDEAL_OUTCOME_AND_CLASSICAL_SCORE_PROOFS_PASS",
          ideal_phase_outcome_rows=rows,
          postprocessing_score=score,
          public_classical_baseline=baseline,
          descriptive_post_scoring_order_verification=order,
          postprocessing_derived_from_only_public_a_N_k=True,
          ideal_distribution_complete=True,
          actual_quantum_device_shots=0,
          success=True
        )
        save()
        print("N35 IDEAL QFT OUTCOME SUMMARY",base,
          json.dumps(dict(ideal_strict=score["strict_cf_ideal_success_probability"],
             ideal_bounded=score["bounded_4_public_multiples_ideal_success_probability"],
             uniform_strict=score["strict_cf_uniform_fourbit_k_baseline"],
             uniform_bounded=score["bounded_cf_uniform_fourbit_k_baseline"],
             zero_outcome_probability=rows[0]["ideal_probability"],
             public_gcd_classical_preempts=baseline["pre_qft_classical_gcd_preempts_quantum_claim"]),
             sort_keys=True), "ZERO QPU",flush=True)
        return 0
    except Exception as exc:
        receipt.update(status="FAIL",success=False,
            error_type=type(exc).__name__,
            error_message=str(exc)[:1800],
            error_traceback=traceback.format_exc()[-3500:],
            external_qpu_calls=0,free_quantum_runtime_used=False,
            paid_quantum_runtime_used=False)
        save()
        print("N35 IDEAL DISTRIBUTION PROOF FAIL",base,
              type(exc).__name__,str(exc)[:600],
              traceback.format_exc()[-1300:],"ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",type=int,choices=BASES,required=True)
    args=ap.parse_args()
    raise SystemExit(run_base(args.base))
