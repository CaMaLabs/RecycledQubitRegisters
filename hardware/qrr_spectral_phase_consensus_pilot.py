#!/usr/bin/env python3
"""Zero-QPU phase-consensus pilot inspired by Alosh Denny's reverse-SynthID.

This is original, standalone implementation of elementary circular stats,
NOT a copy of reverse-SynthID code or a new factoring/oracle method.
Research lead Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from dark_star_full_qpe_outcome_holdout import full_qpe_probabilities

Q=256
M=8
SHOTS=2048
REPEATS=32
TRAIN_NULL=128
TEST_NULL=64
FROZEN="QRR-phase-consensus-null-v1-20261016"
OUT=Path("results/dark_star_ptp/qrr_spectral_phase_consensus_pilot.json")


def rng_for(*parts):
    seed=int.from_bytes(hashlib.sha256("|".join(map(str,(FROZEN,*parts))).encode()).digest(),"big")
    return np.random.default_rng(seed%(1<<128))


def sampled_blocks(probs,tag,rep,shuffle=False):
    rng=rng_for(tag,rep)
    rows=[]
    for i in range(M):
        hist=rng.multinomial(SHOTS,probs).astype(float)
        if shuffle:
            hist=hist[rng.permutation(Q)]
        rows.append(hist)
    return np.asarray(rows)


def phase_coherence(blocks,k):
    mean_centered=blocks-blocks.mean(axis=1,keepdims=True)
    fft=np.fft.rfft(mean_centered,axis=1)
    coeff=fft[:,k]
    unit=np.divide(coeff,abs(coeff),out=np.zeros_like(coeff),where=abs(coeff)>1e-12)
    return float(abs(unit.mean()))


def run():
    results={}
    for order in (4,6):
        P,diag=full_qpe_probabilities(order,8)
        assert len(P)==Q and abs(float(P.sum())-1)<1e-10
        uniform=np.full(Q,1/Q)
        rng=rng_for("permanent-instrumental-artifact",order)
        artifact=uniform.copy()
        # Stable apparatus artifact, NOT the legitimate QPE order signature.
        artifact[17]+=.10
        artifact/=artifact.sum()
        k=order
        training=[phase_coherence(sampled_blocks(uniform,(order,"training-null"),i,shuffle=True),k)
                  for i in range(TRAIN_NULL)]
        threshold=float(np.quantile(training,.95))
        controls={
          "permuted_qpe_null":[phase_coherence(sampled_blocks(P,(order,"permuted"),i,shuffle=True),k)
                               for i in range(TEST_NULL)],
          "uniform_sham":[phase_coherence(sampled_blocks(uniform,(order,"white"),i),k)
                          for i in range(TEST_NULL)],
          "stable_fixed_bin_artifact":[phase_coherence(sampled_blocks(artifact,(order,"apparatus"),i),k)
                                       for i in range(TEST_NULL)]}
        signal={}
        for contam in (0,.15,.35):
            mixed=(1-contam)*P+contam*uniform
            values=[phase_coherence(sampled_blocks(mixed,(order,"signal",contam),i),k)
                    for i in range(REPEATS)]
            signal[str(contam)]={"mean_coherence":float(np.mean(values)),
              "median_coherence":float(np.median(values)),
              "hit_rate":float(np.mean(np.asarray(values)>threshold)),
              "trials":len(values)}
        rows={name:{"false_positive_rate":float(np.mean(np.asarray(values)>threshold)),
            "median_coherence":float(np.median(values)),
            "trials":len(values)} for name,values in controls.items()}
        # Frozen gate uses *independent* permuted and uniform negative controls.
        pass_gate=(
             signal["0"]["hit_rate"]>=.75 and signal["0.15"]["hit_rate"]>=.75
             and rows["permuted_qpe_null"]["false_positive_rate"]<=.10
             and rows["uniform_sham"]["false_positive_rate"]<=.10)
        results[str(order)]={"r_validation_only":order,"Q":Q,
           "harmonic_k":k,"full_QPE_probability_fft_normalized":True,
           "training_null_count":TRAIN_NULL,"test_null_count":TEST_NULL,
           "threshold_95pct_training_null":threshold,
           "signal":signal,"controls":rows,
           "primary_synthetic_gate_pass":bool(pass_gate),
           "stable_artifact_can_false_positive":rows["stable_fixed_bin_artifact"]["false_positive_rate"]>.10}
        print(f"r={order} threshold={threshold:.3f} "
              f"0/15/35pct_signal={[round(signal[str(x)]['hit_rate'],3) for x in (0,.15,.35)]} "
              f"permute_FPR={rows['permuted_qpe_null']['false_positive_rate']:.3f} "
              f"uniform_FPR={rows['uniform_sham']['false_positive_rate']:.3f} "
              f"persistent_artifact_FPR={rows['stable_fixed_bin_artifact']['false_positive_rate']:.3f} "
              f"gate={pass_gate}",flush=True)
    assert all(z["full_QPE_probability_fft_normalized"] for z in results.values())
    obj={"revision":FROZEN,"date_utc":datetime.now(timezone.utc).isoformat(),
      "lead":"Chase Lunsford / CaMaLabs",
      "external_inspiration":"Alosh Denny, reverse-SynthID (independent elementary circular statistics; no borrowed code/data)",
      "zero_QPU":True,"qpu_jobs_submitted":0,
      "phase_resolution_Q":Q,"independent_blocks":M,"shots_per_block":SHOTS,
      "replications_per_signal_condition":REPEATS,
      "claims_boundary":"Synthetic known-order ideal QPE histograms; no order discovery, factoring performance, real QPU evidence or novel theorem",
      "orders":results,
      "combined_primary_pass":bool(all(r["primary_synthetic_gate_pass"] for r in results.values())),
      "adversarial_stable_artifact_exposes_non_specific_coherence":bool(any(r["stable_artifact_can_false_positive"] for r in results.values()))}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(obj,indent=2)+"\n")
    print("SYNTHETIC PHASE CONSENSUS", "PASS" if obj["combined_primary_pass"] else "FAIL",
      "ARTIFACT WARNING",obj["adversarial_stable_artifact_exposes_non_specific_coherence"],
      "ZERO QPU",OUT,flush=True)


if __name__=="__main__":
    run()
