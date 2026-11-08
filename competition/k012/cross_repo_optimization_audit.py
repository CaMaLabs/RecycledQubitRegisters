#!/usr/bin/env python3
"""K012: cross-repository optimization integration and qubit-liveness reconnaissance.

Inputs: locally exported official Kaggle KMx, locally cloned QRR and LWE
repos (optional for source-path validation). Outputs: explicit applicability
matrix, liveness lower bounds, scoring sensitivities, and experiment order.

Static analysis only. No rewriting or claim of provable recycling.
Avoid assuming HMR/R frees a qubit or that an unused qN index is reusable.
"""
from __future__ import annotations
import argparse, collections, json, re
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
KMX=(PROJECT/"competition/k001/private/runs/k005/reference_roundtrip.kmx")
OUT=HERE/"k012_cross_repo_integration.json"
QBIT=re.compile(r"(?<![A-Za-z0-9_])q(\d+)(?![A-Za-z0-9_])")
TRACKS=[
 ("QRR","A110 commutation-aware involution cancellation","docs/QRR_A110_COMMUTATION_CANCELLATION.md","implemented","K006/K008 confirmed zero score change; expand only with exact proofs"),
 ("QRR","A97 adaptive modular-arithmetic construction","hardware/qrr_a97_adaptive_full_modular_multiplier.py","requires_arithmetic_matching","Only transplant to proven matching arithmetic subcircuits, not arbitrary invsqrt blocks"),
 ("QRR","A114 constructive Clifford+T costing","docs/QRR_A114_CONSTRUCTIVE_CLIFFORD_T_AUDIT.md","resource_accounting","Translate exact non-Clifford cost to competition verifier's actual gate counting; do not equate costs blindly"),
 ("QRR","recycled registers, live ancilla reuse","docs/DARK_STAR_RECYCLED_SCALABLE_ARITHMETIC_AUDIT.md","lifetime_analysis","Check live ranges; HMR/R does not automatically mean immediately reusable"),
 ("QRR","carry/borrow, prefix and ripple arithmetic","docs/QRR_N35_ARITHMETIC_REPLACEMENT_RESULT.md","requires_arithmetic_matching","Prove function and phase-equivalence with official verifier"),
 ("QRR","carry-save full multiplier A106 negative result","docs/QRR_A106_CSA_CONTROLLED_MULTIPLIER.md","negative_control","Track as candidate only if a new workload-specific gate/ancilla budget supports it"),
 ("QRR","A109 per-constant adder selection","docs/QRR_A109_FULL_MULTIPLIER_SELECTOR.md","negative_control","Do not automatically promote historical negative variants"),
 ("QRR","Dark Star bounded branch-and-bound candidate search","docs/QRR_A96_DYADIC_WRAP_PREFIX_RESEARCH.md","search_controller","Use bounded static cost bounds to avoid expensive verifier runs"),
 ("QRR","measurement-based uncomputation and feedforward","docs/QRR_A107_FULL_QPE_INTEGRATION_AUDIT.md","requires_phase_proof","No rewrite across HMR/R/CZ or conditions until phase and classical feedback verified"),
 ("QRR","comparator, constant conjugation and sign selection","docs/QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_RESULT.md","requires_arithmetic_matching","Enable only when exact operator matches an extracted block"),
 ("LWE","finite-field Fourier/NTT structure","docs/joint_ntt_propagation.md","analysis_only","Use on matched finite-field arithmetic blocks; not generic phase reduction"),
 ("LWE","public dual Fourier and noise response","docs/mlkem512_public_dual_fourier_verified.md","not_directly_transferable","LWE encryption-noise statistics are not equivalent to kickmix measurement randomness"),
 ("LWE","local support pruning with boundary constraints","docs/mlkem512_local_y_support_pruning.md","search_controller","Use truth-preserving bounds for candidate rewrites; no oracle-frozen outside variables"),
 ("LWE","adaptive rotation/geometry preconditioning","docs/mlkem512_adaptive_rotation_frontier_verified.md","search_controller","Rank search branches only; no claim of circuit equivalence"),
 ("LWE","bounded-neighbor recursive pruning","docs/mlkem512_bounded_neighbor_prune.md","search_controller","Keep a reference-equivalent candidate as the invariant"),
 ("LWE","exact-box, modular dual certificates, BKZ/LLL","experiments/mlkem512_publickey_primal_ladder.py","not_directly_transferable","Lattice decoding is not a kickmix compiler rewrite"),
 ("LWE","polynomial constraint and NTT support propagation","experiments/mlkem512_ntt_support_probe.py","requires_arithmetic_matching","Consider only if circuit contains compatible modular polynomial subroutines"),
]
def audit(lines):
 first,last,counts={}, {},collections.Counter()
 dynamic=collections.Counter()
 op_count=collections.Counter()
 timeline=collections.defaultdict(list)
 for i,line in enumerate(lines):
  tokens=line.strip().split()
  if not tokens:continue
  name=tokens[0]
  op_count[name]+=1
  if name in {"INFO_TAG","REGISTER","APPEND_TO_REGISTER"}:continue
  qs={int(s) for s in QBIT.findall(line)}
  for q in qs:
   first.setdefault(q,i);last[q]=i;counts[q]+=1
   timeline[q].append(name)
  if name in {"HMR","R","PUSH_CONDITION","POP_CONDITION","Z_POW","NEG","RESET","FREE"}:
   dynamic[name]+=1
 if not first:return {"error":"No qN references in KMx"}
 n=len(lines)
 ranges=[(first[q],last[q],q) for q in first]
 # This is merely a span overlap upper bound on reallocation possibilities:
 # truly live registers need semantic initialization/reset and verified cleanup.
 events=collections.Counter()
 for begin,end,q in ranges:
  events[begin]+=1;events[end+1]-=1
 running=0;peak=0;peak_line=0
 for line,delta in sorted(events.items()):
  running+=delta
  if running>peak:peak=running;peak_line=line+1
 op_n=op_count.get("CCX",0)+op_count.get("CSWAP",0)+op_count.get("CCZ",0)
 return {"total_instructions":n,"instruction_counts":dict(op_count.most_common()),
  "distinct_quantum_operand_indices":len(first),
  "span_overlap_peak":peak,"span_overlap_peak_line":peak_line,
  "note":"Span overlap is not certified live-ancilla count; it ignores initialization/reset, quantum entanglement and feedback",
  "first_last_reference_examples":[{"q":q,"first":first[q]+1,"last":last[q]+1,"references":counts[q]}
    for q in sorted(first,key=lambda q:(-counts[q],q))[:20]],
  "singleton_operands":sum(v==1 for v in counts.values()),
  "dynamic_markers":dict(dynamic),
  "toffoli_like_static":op_n,
  "score_if_260_qubits_and_reference_C":260*7935.48570915309,
  "illustrative_one_qubit_savings_if_C_constant":7935.48570915309,
  "illustrative_one_toffoli_savings_if_Q_260":260}
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--kmx",type=Path,default=KMX)
 a.add_argument("--output",type=Path,default=OUT)
 args=a.parse_args()
 if not args.kmx.exists():a.error("Missing K005 exported KMx")
 lines=args.kmx.read_text(encoding="utf-8").splitlines()
 profile=audit(lines)
 data={"status":"PASS_CROSS_REPO_APPLICABILITY_AND_STATIC_LIVENESS",
       "project":"Google Quantum AI Verifiable Quantum Circuit Compilation",
       "inputs":{"kmx":str(args.kmx),"qrr_repo":str(PROJECT),
                 "lwe_repo_url":"https://github.com/CaMaLabs/LWE_GeometryLab"},
       "techniques":[{"repo":repo,"name":name,"source_path":path,"stage":stage,
                      "validation_constraint":note} for repo,name,path,stage,note in TRACKS],
       "lifetime_audit":profile,
       "integration_policy":{"exact":True,"unproven_substitutions_accepted":False,
                            "measurement_rewrite_without_phase_proof":False,
                            "compare_actual_Q_times_C":True,"preserve_negative_controls":True,
                            "run_official_verifier_on_every_finalist":True},
       "status_detail":"Audit/planning executable, NOT a claimed implementation of every technique",
       "candidate_modified":False,"verifier_passed":False,"submitted":False}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(data,indent=2)+"\n")
 print("K012 STATUS",data["status"])
 print("K012 METHODS",len(TRACKS),"QRR",sum(t[0]=="QRR" for t in TRACKS),"LWE",sum(t[0]=="LWE" for t in TRACKS))
 print("K012 LIFETIME",{"unique_qubits":profile.get("distinct_quantum_operand_indices"),
       "span_overlap_peak":profile.get("span_overlap_peak"),
       "peak_line":profile.get("span_overlap_peak_line"),
       "single_reference_qubits":profile.get("singleton_operands")})
 print("K012 DYNAMIC",profile.get("dynamic_markers"))
 print("K012 EXPERIMENT GATES",data["integration_policy"])
 print("K012 NOTE",data["status_detail"])
 print("K012 REPORT",args.output)
if __name__=="__main__":main()
