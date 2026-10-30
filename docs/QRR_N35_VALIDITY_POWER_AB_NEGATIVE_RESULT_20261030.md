# N35 validity comparator transplant — negative native result

Research lead Chase Lunsford / CaMaLabs. 2026-10-30.

Source: user-executed `python hardware/qrr_n35_validity_power_ab.py --native` and subsequent local JSON summary. Result file remains on user's Ubuntu workstation at `results/qrr_n35_validity_power_ab/controlled_powers_ab.json`; raw JSON is NOT archived in this commit. Native CPU transpilation uses Fez metadata, no QPU jobs.

All six public nonidentity controlled powers 2,4,8,11,16,29 passed phase-exact full-register 128/128 baseline and candidate cases, with clean auxiliaries. 48 CPU Fez compilations completed (6 powers × 4 seeds × 2 arms). No observed hardware performance, zero QPU runtime.

| Power | Seeds simultaneous CZ/depth win | Median candidate−baseline CZ | Median candidate−baseline depth | Preregistered 3/4 gate |
|---|---:|---:|---:|---|
| 2 | 0/4 | +176 | +616 | FAIL |
| 4 | 1/4 | +290 | +129.5 | FAIL |
| 8 | 0/4 | +170.5 | +444.5 | FAIL |
| 11 | 1/4 | +73.5 | +356.5 | FAIL |
| 16 | 1/4 | −128.5 | +217 | FAIL |
| 29 | 1/4 | −9 | +331 | FAIL |

**Decision:** Reject candidate as native Fez optimization. Preserve its exact-source correctness and standalone gate savings as narrow results. No full dynamic b4/b6/b8 benchmark, no IBM QPU submission. Do not describe `NATIVE_DONE` as a resource win. Future changes should target dominant modular arithmetic and routing hotspots; require pre-registered matched seeds, exact phase and cleanup before native read.
