# A13 Fez branch-calibration audit — user-run result, 2026-10-30

24 read-only IBM Fez native CPU compilations, zero QPU jobs. All report calibration coverage `1.0`, but this fraction is a count among modeled instructions, not proof of physically complete calibration. Dynamic conditional blocks: b4=6, b6=15, b8=28. Reported nested operations match these counts, requiring independent confirmation of branch-body handling. Log-risk is an **unweighted all-branch surrogate**, NOT observed shot failure, independent BER, or QPU-derived phase error.

|Base|Phase bits|Lowest reported log-risk|Seed|Values over four seeds (509,1223,4093,8776)|
|---:|---:|---:|---:|---|
|2|4|83.02|4093|86.00,117.88,83.02,111.62|
|2|6|127.53|1223|165.52,127.53,137.56,164.26|
|2|8|181.61|4093|186.76,226.12,181.61,219.09|
|8|4|41.25|1223|44.46,41.25,43.49,45.90|
|8|6|41.51|1223|44.48,41.51,43.54,45.92|
|8|8|41.78|1223|44.49,41.78,43.60,45.93|

Do not translate log-risk to readout BER or decide actual hardware experiment on this basis. Preserve Quaspy, recycling, and original selected arithmetic baselines. Next audit: structural branch-body gate counts and phase precision semantics independent of calibration; avoid converting all-branch sums to shot fidelity.
