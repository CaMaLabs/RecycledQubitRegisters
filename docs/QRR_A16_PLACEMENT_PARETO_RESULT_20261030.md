# A16 placement Pareto — user execution 2026-10-30

`python hardware/qrr_a16_placement_pareto.py` returned `PASS_PARTIAL_CALIBRATION`, zero QPU jobs. Pareto criterion combines native CZ, depth, mean physical measurement calibration and incomplete all-branch log-risk; reset calibration unavailable. No actual QPU readout fidelity or factoring rate established.

|Base|bits|Pareto seeds|Min CZ|Min depth|Min measure error|Min partial log risk|
|---:|---:|---|---:|---:|---:|---:|
|2|4|509,1223,4093,8776|4093|4093|1223|4093|
|2|6|509,1223|1223|1223|509|1223|
|2|8|509,1223,4093|4093|509|1223|4093|
|8|4|509,1223,4093|1223|1223|509|1223|
|8|6|509,1223,4093|1223|1223|509|1223|
|8|8|509,1223,4093|1223|1223|509|1223|

The base8 objective conflict makes seeds509 and1223 useful matched reference layouts for further calibration sensitivity, but does **not** justify claiming improved real output fidelity. A16 combined existing A13/A15 data, no new compilation. Never treat its objective as a probabilistic circuit success estimate. Preserve historical arithmetic, Quaspy, and N35 dynamic results.
