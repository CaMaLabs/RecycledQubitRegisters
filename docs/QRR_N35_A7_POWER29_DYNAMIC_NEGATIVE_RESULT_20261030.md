# A7 — power29 k23 selective full dynamic recycled-phase result, 2026-10-30

Research lead Chase Lunsford / CaMaLabs. User-executed `python hardware/qrr_n35_a7_power29_dynamic_ab.py --native` in Ubuntu IBM Open-plan Qiskit environment. Full raw result is local `results/qrr_n35_a7_power29_dynamic_ab/results.json`, not committed here.

Executed 48 read-only IBM Fez native CPU compilations (bases2/8 × b4/b6/b8 × four seeds × two arms). Zero QPU jobs, no real hardware runtime consumed. A7 source checks completed and existing six public power source proofs were used.

|Configuration|K23 substitutions|Both metric wins|Median candidate-baseline CZ|Median candidate-baseline depth|Decision|
|---|---:|---:|---:|---:|---|
|base2 b4|0|0/4|0|0|No-op control|
|base2 b6|0|0/4|0|0|No-op control|
|base2 b8|0|0/4|0|0|No-op control|
|base8 b4|1|0/4|+139.5|+1224|FAIL|
|base8 b6|1|0/4|+139.5|+1224|FAIL|
|base8 b8|1|0/4|+139.5|+1224|FAIL|

**Disposition:** A7 rejected as a whole-circuit optimization. Earlier standalone k23 A5 and isolated power29 A6 improvements remain real within their stated scope and should not be promoted as dynamic circuit improvements. Preserve original selected arithmetic. Next efforts should profile compiled routing and critical-path hotspots, compare structurally different carry networks, and keep gate-exact phase/clean semantics. The result does not establish practical RSA factoring or ML-KEM cryptanalysis.
