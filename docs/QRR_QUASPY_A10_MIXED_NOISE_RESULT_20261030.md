# Quaspy A10 mixed-noise synthetic result — user-executed, 2026-10-30

Command: `hardware/qrr_quaspy_a10_mixed_noise.py --upstream /tmp/qrr-indie-quaspy --max-pairs 0` from PR #14-derived branch. `status=PASS`, 512 paired samples per profile, zero QPU jobs. All arms had zero `WORK_LIMIT` exits.

|Profile|CF factors|Quaspy factors|Uplift (percentage points)|CF modular powers per factor|Quaspy modular powers per factor|
|---|---:|---:|---:|---:|---:|
|clean|152/512|398/512|48.046875|38.0263|115.4095|
|low|151/512|395/512|47.65625|38.2715|117.8329|
|medium|143/512|356/512|41.6015625|40.1119|138.5787|
|high|123/512|291/512|32.8125|46.4634|196.5258|
|severe|86/512|181/512|18.5546875|64.9070|357.5635|
|uniform|0/512|0/512|0|undefined|undefined|

Limitations: seeded mixtures of frequency offsets and uniform corruption are not a hardware-calibrated IBM Fez measurement/decoherence model. Quaspy remains costlier classically; no evidence of physical QPU speedup or RSA-2048 break. Raw JSON remains on user's Ubuntu worktree. Next: phase-register-native corruption (bit flips and readout confusion) and cost-bounded selection policy on frozen heldout data without leaking true factors.
