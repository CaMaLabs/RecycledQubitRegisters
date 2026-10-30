# A5 five-hotspot complement-conjugated adder — native result (2026-10-30)

Research lead: Chase Lunsford / CaMaLabs. User executed `hardware/qrr_n35_a5_hotspot_complement_ab.py --native` locally in existing IBM/Qiskit environment; raw JSON is on the user's Ubuntu machine at `results/qrr_n35_a5_hotspot_complement_ab/results.json`, **not committed here**.

All 5 hotspot constants (11,13,17,23,29) passed 99 basis input checks per arm, exact +1 computational phase, and auxiliary cleanup. 40 native Fez target CPU compilations (5 constants × 4 paired seeds × 2 variants), **zero QPU jobs**.

| k | Both-CZ-and-depth improvement seeds | Median delta CZ (complement-selected) | Median delta depth | 3/4 native criterion |
|---|---:|---:|---:|---|
| 11 | 0/4 | +27 | +81.5 | FAIL |
| 13 | 1/4 | +4.5 | +46 | FAIL |
| 17 | 0/4 | +4.5 | +28 | FAIL |
| 23 | **3/4** | **-22** | **-72.5** | **PASS** |
| 29 | 1/4 | +2.5 | +35.5 | FAIL |

**Decision:** preserve standalone k=23 win only, reject the other four as native improvements. Next step is selective k=23 substitution in whole public controlled powers and b4/b6/b8 dynamic circuits, with exact phase, all 64 work states and full auxiliary cleanup before native scoring. Do not claim physical QPU improvement, new Gidney/dirty ancilla construction, RSA breakthrough, or ML-KEM result. Full-circuit advantage is **unverified**.
