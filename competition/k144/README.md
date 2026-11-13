# K144 — Paired Helios phase-headroom experiment (candidate NOT YET VERIFIED)

## Decision after K027 reconstruction

Source evidence from user-supplied K001–K097 archive shows:
- `competition/k027/method_registry.json` explicitly has `integration_complete: false`.
- `k027/fusion_methods.py` mutates precision, scalar/grouped mode, and existing schedules. It does **not** implement FFT/NTT arithmetic, new register recycling, or new reversible arithmetic architectures.
- `k027/k027_status.json` shows **48 candidates**, six partial verifier passes through x=512; reference 260q, 7,735 source Toffolis. No direct application to 62q Helios; do not restart the old evolutionary campaign.

## New narrowly scoped hypothesis

**Joint coordinated perturbation of two q28 Z_POW phase sites** (positive delta / negative delta) may produce a better worst-case phase margin than one-site changes, without increasing qubit count, executed Toffoli count, or arbitrary rotation count. A larger safe global synthesis epsilon can decrease official T-equivalent cost even with the same 41 rotations.

This is distinct from K098 one-site perturbation and K126 individual dyadic rounding. **Opposite source-angle increments do not automatically cancel** because arithmetic and routing separate the phase sites: only the official verifier can validate the phase and measurement semantics.

## Falsification gates

1. Require pinned KMX SHA256 `e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183`, 62 qubits, 42 q28 source phase sites.
2. Never touch baseline. Create uniquely named KMX and KMB candidates. Reject representation-no-op candidates.
3. Compare every candidate against the **same seed and same x-prefix** baseline with the real `k031_full_domain_repair.verify` wrapper. `status=PASS` and strictly **lower score**, not only smaller error ratio, is required to proceed.
4. Optional --full: full-domain x=3,133,452 verification for at most two prefix winners; require two full-domain seed passes, both with score below **95,369.00696815242** before reporting a robust win.
5. Stop/record negative results, including candidates whose value gets rounded away during binary serialization. No Kaggle submission is automatic.

## Status

A self-contained, 8.3KB Python driver has been generated and syntax/self-tested in the ChatGPT analysis workspace, available for download in the conversation as `k144_joint_phase_headroom.py`. **The pinned KMX, Kickmix runtime, and private official verifier are only on the user's Ubuntu VM; no K144 Helios candidate has been run or verified here.**

The normal expectation is **NO WIN**: the baseline's worst relative phase error already nearly saturates tolerance. The value of this bounded experiment is a direct, falsifiable scored candidate mechanism rather than another gate-statistics survey.

Commands on the user's VM once the script is copied to `competition/k144/k144_joint_phase_headroom.py`:

```bash
cd ~/quantum-a26-check
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k144/k144_joint_phase_headroom.py --dry-run
"$PY" competition/k144/k144_joint_phase_headroom.py --max-candidates 24 --prefix-x 4095
# Only if prefix improves and measured result justifies full verification:
"$PY" competition/k144/k144_joint_phase_headroom.py --max-candidates 24 --prefix-x 4095 --full --max-full 2
```

Results: `competition/k144/results/summary.json`. Do not rerun an existing source-profile, K027 recombination, or other unscored optimization as a substitute.

## Actual K144 run reported 2026-11-12 (user VM)

Command: `--max-candidates 24 --prefix-x 4095 --full --max-full 2`. Baseline prefix score `95373.34975366836` (seed 12345, 62q). `K144_RESULT` reported **24 tested, 2 prefix wins, 2 full checks, winner null**.

- `pair004_L25762_25772_p40_s+1`: prefix `95373.3497449065` (a marginal ~0.000008762 reduction); full-domain score `95448.33076494031`, **worse** than 95369.00696815242 by ~79.324.
- `pair016_L25762_25772_p36_s+1`: same prefix score `95373.3497449065`; `FULL_NO_WIN`, no printed full score. Examine `summary.json` for error, fail ratio or timeout before claiming the exact reason.
- Multiple `K144_CASE` rows have `prefix_score: null`, and were printed as `NO_PREFIX_WIN`. This output alone does not distinguish official validation rejection from timeout/parser problems; inspect complete per-case result objects.
- No verified winning circuit. **Do not repeat an enlarged grid without diagnosing failures and forming a scored mechanism.**

**Provenance:** Results transcribed from user's 2026-11-12 terminal output. Full `competition/k144/results/summary.json` not yet inspected remotely.

## Detailed K144 failure diagnosis (2026-11-12, user-provided summary extract)

The first uploaded console trace was ambiguous because the driver printed only `score`, resulting in null for failed verification. The user subsequently supplied full nested `prefix` and `full_12345` objects:

- Pair004 (`L25762_25772_p40_s+1`) prefix `PASS`, score 95373.3497449065, `rotation_eps=2.4340415639502205e-13`; full-domain `PASS`, score **95448.33076494031**, `rotation_eps=2.085594910926685e-13`, 62q, 41 arbitrary rotations, 1 T, mean Toffoli-like **1243.118965920014** (source unchanged in scored-gate counts). The lower global allowable rotation epsilon worsened synthesized T cost. Full worst ratio 0.9993237694056958 at x=161. Source change **not** a win.
- Pair016 (`L25762_25772_p36_s+1`) prefix `PASS`, same prefix score, but full `FAIL` at x=219108: phase error `1.293e-10` turns vs tolerance `1.273e-10`.
- Pair014 failed prefix at x=792; pair015 at x=221; pair017,020,022 at x=644; pair021 at x=161; pair023 at x=221. They are **phase tolerance rejects**, not timeouts.
- K144 reported 24 cases, two prefix wins, two full checks, zero full-domain lower-score winners. Prefix-winning deltas were microscopic (~8.76e-6 score units) and non-predictive.

**Disposition: CLOSED NEGATIVE.** Do not expand unstructured two-site opposite-angle scans. A future phase-candidate needs an analytically justified, globally bounded margin improvement, not a shallow prefix score difference. Driver's `prefix_score: null` on validation failure should be interpreted from full `prefix.error`, not as an unknown runtime error.
