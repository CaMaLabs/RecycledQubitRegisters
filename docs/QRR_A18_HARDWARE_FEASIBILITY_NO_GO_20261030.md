# A18 Fez hardware feasibility — user-run 2026-10-30

`python hardware/qrr_a18_hardware_feasibility_gate.py` executed after pulling commit `ba2e91b`. Output `CPU_GATE_NO_GO`, `qpu_jobs=0`, matched pair go=false. Read-only target CPU compilation.

|Seed|Native CZ|Native depth|Mean calibrated readout assignment error|Decision|
|---:|---:|---:|---:|---|
|509|14857|34038|0.00732421875|NO_GO|
|1223|14097|32814|0.0943603515625|NO_GO|

Predeclared strict thresholds: at most 1000 CZ and depth3000. Both candidates fail by large factors. This does not measure full circuit readout BER or hardware fidelity; reset calibration and dynamic timing are incomplete. Do not submit a QPU job for these circuits. Preserve established N35 arithmetic, physical mapping, Quaspy public-only postprocessing and PR branches. Pursue lower-depth architecture plus exact source/circuit semantics before reconsidering hardware.
