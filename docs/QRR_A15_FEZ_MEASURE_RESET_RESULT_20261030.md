# A15 Fez measurement and reset calibration — user-executed 2026-10-30

24 read-only backend CPU compiles, 0 QPU jobs. **Every reset calibration was `None`; `calibration_complete=false` for all six configurations.** Mean calibrated measurement errors by seed 509,1223,4093,8776:

|base|bits|509|1223|4093|8776|minimum mean error seed|
|---|---|---:|---:|---:|---:|---:|
|2|4|0.0367431640625|0.0054931640625|0.0419921875|0.00830078125|1223|
|2|6|0.0048828125|0.00821940104167|0.0426432291667|0.0419921875|509|
|2|8|0.01708984375|0.0098876953125|0.03619384765625|0.04156494140625|1223|
|8|4|0.00732421875|0.0943603515625|0.0225830078125|0.0225830078125|509|
|8|6|0.00732421875|0.104085286458|0.0235188802083|0.0174967447917|509|
|8|8|0.00732421875|0.10894775390625|0.02398681640625|0.01495361328125|509|

For base8 b8, seed 509 mean measurement error 0.7324%, seed1223 10.8948%, a ~14.9x difference. However seed1223 was best on A13 *partial log-risk* proxy. This confirms differing optimization objectives; it does NOT prove 14.9x better effective phase fidelity, real measurement error, or factoring success. The phase qubit has reused physical locations, and per-measurement calibration is not a complete dynamic device model. Preserve source semantics, original arithmetic, and Quaspy. Next: recover reset reliability or explicitly exclude reset error; develop Pareto mapping criteria and distinguish readout-only, gate-only and joint estimates before any QPU approval.
