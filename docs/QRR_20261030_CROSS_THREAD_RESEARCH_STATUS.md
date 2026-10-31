# Research report consolidation — October 30, 2026

Lead: Chase Lunsford / CaMaLabs.

This file is an index of already committed experimental summaries and unmerged Work-mode research, **not a substitute for missing raw local files**. Do not treat unmerged draft PRs as main-branch evidence.

## N35 arithmetic, user-executed Ubuntu read-only Fez-target CPU compiles

- [A5](QRR_N35_A5_K23_SELECTIVE_NATIVE_RESULT_20261030.md): five constants, 40 native compilations; k=23 wins 3/4 paired seeds, four candidates fail.
- [A6](QRR_N35_A6_SELECTIVE_K23_FULL_POWER_RESULT_20261030.md): six public powers, 48 native compilations; power29 wins 3/4, others fail or are unchanged.
- [A7](QRR_N35_A7_POWER29_DYNAMIC_NEGATIVE_RESULT_20261030.md): six complete recycled dynamic circuits, 48 native compilations; affected base8 b4/6/8 each regress median +139.5 CZ, +1224 depth.
- [Corrected ripple comparison](QRR_N35_MODADD_CORRECTED_NATIVE_AB_20261030.md): 272 native compilations, 16 of 34 selected constants show robust wins; first run was an invalid self-comparison and excluded.

Local raw files still require archival from the user's machine:
`results/qrr_n35_a5_hotspot_complement_ab/results.json`,
`results/qrr_n35_a6_k23_full_power_ab/results.json`,
`results/qrr_n35_a7_power29_dynamic_ab/results.json`,
`results/qrr_n35_modadd_ripple_screen/screen.json`.
Never fabricate these data or replace them with the shorter summaries.

## Work-mode draft pull requests (unmerged as of review)

- [PR #13](https://github.com/CaMaLabs/RecycledQubitRegisters/pull/13) tests Gidney-style measurement-based adder. Reported 486,224 exact input/measurement paths, but complete N35 substitution loses 8/8 native comparisons: +24.6% to +51.0% CZ, still 23 active qubits. Stacked on #12; review dependency before merging.
- [PR #14](https://github.com/CaMaLabs/RecycledQubitRegisters/pull/14) implements public-input Quaspy order-finding postprocessing. Frozen synthetic ideal readouts: shorter Quaspy 398/512 verified factor successes vs conventional full-precision CF 152/512 (77.73% vs 29.69%). Four fewer phase bits. 50/64 clusters improved, 14 tied, none worsened. Seven contract tests and 512 public-input-only replays reported. Quaspy raises classical workload; not an RSA-2048 attack or QPU timing benchmark. Stacked on #13. Contains lossless raw `results/indie_diamond_20261030/audit.json.gz`, summaries and requirements on PR branch.
- In the same PR #14, CADO host arithmetic bridge passes 10,240 CPU checks including 2048-bit operands; CUDA launch and factoring success unverified.

## Next action gate

Do not use the A5/A6 local subcircuit wins as dynamic wins. Archive exact local raw outputs, preserve PR #13/#14 branches and run Quaspy's pinned, public-input-only replay and seven tests independently. Then compare the postprocessor with the actual N35 noisy or simulated readout distributions, not synthetic ideals alone. No paid QPU/runtime jobs.
