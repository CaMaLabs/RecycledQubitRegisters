# Quaspy independent full audit rerun (user Ubuntu) — 2026-10-30

Command executed in PR #14 worktree: `.venv/bin/python hardware/qrr_indie_diamond_audit.py --upstream /tmp/qrr-indie-quaspy --output /tmp/qrr-indie-rerun`.

Terminal reported completion of replication and holdout for 32,48,64,96 bits. Summary:

```json
{"cluster_wins":50,"cluster_losses":0,"one_sided_sign_p":8.881784197001252e-16,"factor_success_uplift":0.48046875,"phase_round_proxy_ratio":0.369179229480737,"uniform_null_factor_rate":0.0,"passed":true}
```

This independently reruns the scripted synthetic benchmark on user's Ubuntu; complete generated JSON artifacts are at `/tmp/qrr-indie-rerun` on that machine and are **not** included in this commit. Relative to the published PR #14 summary, reported factor-recovery uplift is 48.05 percentage points and phase-round *proxy* improvement about 63.08%. This is simulation/postprocessing evidence, not real quantum hardware performance, real-key factorization, or confirmation of complete unit-test suite (no unit-test log was supplied).

Next needed: noise robustness and work-vs-yield sweeps on measurement readouts, preserving public-only input contract and null controls.
