# A17 placement-to-Quaspy readout sensitivity — user-run result, 2026-10-30

User ran `hardware/qrr_a17_readout_placement_sensitivity.py --upstream /tmp/qrr-indie-quaspy --pairs 128` on independent PR worktree. Printed `PASS_SENSITIVITY_ONLY`, 128 held-out synthetic readout pairs per scenario; no QPU jobs or work-limit failures.

|Scenario|Independent-bit-flip assumption|CF verified|Quaspy verified|CF modular powers/factor|Quaspy powers/factor|
|---|---:|---:|---:|---:|---:|
|clean|0|38/128|95/128|18.9211|124.4737|
|base8 b8 seed509 calibration mean|0.00732421875|24/128|67/128|31|208.6418|
|base8 b8 seed1223 calibration mean|0.10894775390625|0/128|1/128|N/A|21745|

Important: mean assignment-error calibration from a tiny N35 b8 compiled layout is extrapolated to independent error on much longer ideal 32–96-bit synthetic readout registers. This is **not a measured QPU bit-error rate or calibrated factoring forecast**. Missing reset errors, two-qubit gate errors, idle leakage, feedback, correlated noise and shot distributions. This result justifies considering a separately preregistered low-shot matched hardware comparison, not predicting a 52.3% real success rate for seed509 or authorizing hardware automatically. Preserve Quaspy PR and historical baseline.
