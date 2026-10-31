# A19 base8 b4 native stage-cost attribution — user execution, 2026-10-30

Command `python hardware/qrr_a19_native_power_cost_attribution.py`. Status `DIAGNOSTIC_PASS_NOT_SEMANTIC_REPLACEMENT`, zero QPU jobs. The stage-omitted variants are **invalid factoring circuits** used only to quantify compilation changes.

|Seed|Baseline CZ/depth|Omit power8 CZ/depth|Baseline minus omit8 CZ/depth|Omit power29 CZ/depth|Baseline minus omit29 CZ/depth|
|---:|---|---|---|---|---|
|509|14857 / 34038|7490 / 18079|7367 / 15959|7211 / 17061|7646 / 16977|
|1223|14097 / 32814|7778 / 17631|6319 / 15183|7419 / 17307|6678 / 15507|

Active nonidentity powers are 8 and 29. Both account for large source cost and mapped circuit cost. Differences of compiler outputs are NOT additive stage gate counts, nor a proof that each stage's standalone optimization will translate into end-to-end improvement. Existing A18 strict gate (CZ<=1000, depth<=3000) still NO-GO. Preserve selected arithmetic, placement and Quaspy improvements; prioritize a structurally different correct controlled modular-multiplication synthesis, with exact +1 phase and clean ancilla proofs before native comparison.
