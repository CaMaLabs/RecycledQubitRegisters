# Dark Star + recycled-QPE integration

This directory contains the clean research integration between the earlier Dark Star periodic-prime-space experiments and the recycled-register QPE model.

The benchmark uses **self-generated semiprimes only**. Its purpose is to test a heterogeneous routing idea:

1. classical preprocessing / close-factor midpoint pruning,
2. remaining order-finding uncertainty,
3. routing between classical handling and a quantum phase-estimation stage,
4. comparison of wide and recycled-QPE resource models.

It is not presented as a general RSA break. The wheel/residue layer is conventional modular filtering; its clearest measured advantage in these experiments is Fermat-midpoint pruning for deliberately close factors. The lambda/order diagnostics are exploratory.

## Run

From this directory:

```bash
./run_hybrid.sh \
  --trials 20 \
  --shots 1024 \
  --close-bits 28 32 36 40 \
  --close-steps 250000 \
  --quantum-bits 5 6 7 8 \
  --outdir hybrid_results_large
```

The simulator compares ideal/noisy wide-QPE and recycled-QPE behavior and reports modeled register width. Modular-arithmetic ancillas are deliberately excluded equally from the phase-register width comparison; the recycled model does not claim that the full Shor work register disappears.

## IBM hardware

Use the repository-level hardware tools instead of embedding credentials here:

```bash
cd ../..
./hardware/setup_open_plan.sh
source ~/ibm-6c2q-venv/bin/activate
python hardware/save_open_plan_account.py
python hardware/preflight_open_plan.py
```

Then use `hardware/ibm_6c2q_hardware_test.py` for real-QPU dynamic-circuit experiments.


## Unified Dark Star end-to-end research pipeline (2026-10-28)

**NEW IMPLEMENTATION:** `integrations/darkstar_hybrid/darkstar_unified.py` combines the original PTP periodic prime residues and generated kernel factor-pairs; **unpruned** composite-symmetry annotation; bounded public-only conventional and residue-filtered Fermat factor search; public-power2, Pollard p−1, rho and trial; side-by-side full wheel-210/LFK classical baselines; all fixed odd exponents `1,3,5,7,105,1155,15015`; original PTP-conditioned `L=3 iff N mod3=2`; staged head-bounded ideal-QPE measurements; strict on-demand public continued fractions/pow/GCD factor extraction; post-facto PTP root-pair validation; source generic clean-MCX CCX/CX/CSWAP counts and matched wide/recycled logical peak width.

This is an end-to-end **synthetic toy-semiprime demonstration and baseline harness**, NOT a scalable hardware factoring tool, unknown-key-breaking claim or quantum speedup. **Zero QPU, no IBM Runtime, no paid runtime.** Supplying synthetic p/q permits a **private simulator-only ideal eigenphase oracle**; no public base, exponent, classical selection or CF/GCD routine receives hidden p/q/order. The complete classical baseline often factors these tiny Ns before quantum would be useful. Quantum arms in those cases are explicitly *counterfactual* (for mechanism comparison), not a contribution to factoring workload.

Run from the repository root:

```bash
python3 -m unittest integrations.darkstar_hybrid.test_darkstar_unified -v
python3 -m integrations.darkstar_hybrid.darkstar_unified --p 11 --q 19 --base 3 --output results/dark_star_unified/unified_demo_N209.json
python3 -m integrations.darkstar_hybrid.darkstar_unified --p 23 --q 31 --base 19 --output results/dark_star_unified/unified_demo_N713.json
```

The unified algorithm preserves each method's validity boundary: mirror-equivalent PTP residue pairs **cannot** simply be discarded for fixed N, PTP cannot secretly reject Shor orders without proof, odd-power order identity does not guarantee less real gate work, the 65-bin head simulation credits **no omitted-tail successes**, source CCX is NOT compiled/native routing or physical QPU, and wide/recycled comparisons differ in modeled phase width rather than magic elimination of the modular work register.

The new [protocol](../../docs/DARK_STAR_UNIFIED_END_TO_END_PROTOCOL.md) freezes the exact integration scope and zero-QPU expectations. All older individual Dark Star, PTP and Recycled Qubit Registers positive and negative results remain intact and are not retroactively pooled.


### Original PTP / Dark Star v2 midpoint pruning restored and retested (2026-10-28)

An explicit **public-only `M=255255` quadratic-residue midpoint sieve** now runs as a bounded late classical-first stage if the other cheap public methods do not factor the number. It reuses the exact v2 observation that a genuine Fermat midpoint `x` must have `x*x-N` a quadratic residue modulo every small odd wheel prime. It **cannot reject a true factor midpoint**, and unlike the legacy sorted inverse-factor-pair table it uses inexpensive per-prime residue masks. Its budget is **4096 midpoint x coordinates plus 12 exact integer square-root tests**, independently capped; it records modular membership checks, mask setup, total scan time and recovered factors. The earlier unsafe fixed-N factor-pair mirror deletion is NOT enabled.

[Full audited restoration results](../../docs/DARK_STAR_N26_RESTORED_MIDPOINT_PRUNING_RESULT.md) · [Original frozen N26 input/output receipts](../../results/dark_star_unified/unified_n26_all_12_summary.json) · [Secondary corrected classical-only replay](../../results/dark_star_unified/unified_n26_midpoint_restoration_classical_replay.json).

Across the previously frozen 12 N26 cases, the stronger M255255 sieve reduced expensive exact square root checks **median 47×** vs ordinary Fermat; all **181,440 exact modular-residue agreements** with the original M105/M15015 PTP table method held; **zero valid factors were dropped**. It recovered the old N=49,273,331 weak classical budget survivor in **8 square roots + 985 modular masks**, so the after-update classical pipeline factors **12/12** (original initial experiment remains 11/12). **The strict overall speed gate FAILS**: the new sieve outran conventional wheel trial in 7/12 but original LFK kernel search in only 6/12; no practical runtime advantage is established. This is a **post-hoc algorithm revision**, not an additional independent blind holdout. No IBM QPU / paid Runtime.

Do not conflate this classical PTP pruning with separate N35 public identity-controlled-U pruning or the nine-unused-scratch-wire reduction: the latter has not established robust native CZ/depth improvements.
