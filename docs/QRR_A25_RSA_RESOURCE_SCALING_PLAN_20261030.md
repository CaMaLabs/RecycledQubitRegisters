# A25 RSA scaling scenario — 2026-10-30

**Status:** source committed, execution pending. No QPU jobs. No measured CaMaLabs RSA-128–2048 runtime.

## Goal

Separate *published architecture anchors* from **unverified mathematical sensitivity extrapolations** and from CaMaLabs' actual experimental evidence. The A23 exact ideal N35 success probability is not an RSA scaling measurement.

## Published anchor scenarios

1. Gidney (2025), [arXiv:2505.15917](https://arxiv.org/abs/2505.15917): **fewer than** 1 million physical qubits and **less than** 7 days for RSA-2048, assuming 0.1% gate error, 1µs surface-code cycle and 10µs reaction time. Upper bounds are not calibrated measured values. These are not available present-day device specifications.
2. Pappalardo et al (2026-10-28), [arXiv:2610.37839](https://arxiv.org/abs/2610.37839): approximately **22,593 cat qubits** and **3.14 days** for RSA-2048, assuming a 1µs error-correction cycle, 10µs reaction, phase-flip probability 5e-4 and no bit flips in the base noise model. This cat architecture is not directly comparable to surface-code physical qubits and remains theoretical.

## Explicit sensitivity model

The companion stdlib-only script `hardware/qrr_a25_rsa_resource_scenarios.py` computes for n=128/256/512/1024/2048:

- illustrative qubit scaling `Q(n) = Q(2048)*(n/2048)^alpha` (default alpha=1);
- illustrative runtime scaling `T(n) = T(2048)*(n/2048)^beta` (default beta=3).

These are **not predicted physical requirements** for small n: logical/code-distance/magic-state/control overhead and success probabilities are not modeled. Do not add or multiply CaMaLabs source-width reductions, Quaspy recovery gains, Dark Star pruning gains, or hardware assumptions without a matched real circuit and cost model.

Run at no cost from repository root: `python3 hardware/qrr_a25_rsa_resource_scenarios.py`. Adjust `--qubit-exp` and `--time-exp` for sensitivity studies, never to fit a desired claim.

## Required future measured inputs

- Same-cohort public N/a selection and classical-first preprocessing cost.
- Exact modular arithmetic counts and *compiled* gate/depth/width, resets and control latencies.
- Full gate-level dynamic circuit distribution under ideal and noisy execution.
- CF/Quaspy success probability and expected work **for each** distribution.
- Quantified error-correction architecture, failure target, distillation/cultivation and routing costs.
- Classical competitor runtime and resource envelope.
- Gate-level resource scaling at n=128/256/512/1024/2048; label infeasible simulation as such rather than fabricate output.

**Decision:** The 2026-10-30 evidence supports no empirical RSA-sized runtime or factor-breaking advantage from the CaMaLabs combined design. Maintain hardware NO-GO pending gate proofs and realistic resource costs.
