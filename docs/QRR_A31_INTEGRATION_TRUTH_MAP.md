# A31 integration truth map

## Executed unchanged in A31 runner

- A24: public-first wheel gate; already identifies N35 as classically factored.
- A26: ideal Fourier addition mathematical equivalence.
- A27: reversible repeated-MCX logical addition vs ideal Fourier addition.
- A29: public residue wheel four-arm control (NOT original spectral pruning).
- A30: direct imports from original existing PTP `simulation/ptp_hybrid/{core,kernel}.py` and `hardware/dark_star_ptp_shor_audit.py`; original midpoint pruning included.

## Preserved but not executable in the same factoring circuit

- A23: independent exact ideal recycled phase distribution / Quaspy recovery is proven for N35 in previously reported user runs. Its separate environment is optional for A31 via `--a23-command`; its prior success is not an end-to-end speedup.
- Recycled register placement and dynamic circuit results: retain A21 and earlier resource results, but this script does not compile or execute those physical circuit paths.
- The original NTT spectral-support research in `CaMaLabs/LWE_GeometryLab/experiments/ring_ntt_probe.py`, and ML-KEM public local Fourier/coherence experiments, concern ring-LWE distributions and do not directly prune RSA factors. No cross-domain gain claimed. Do not substitute modulo-210 wheel pruning for these experiments.

## Acceptance gates for actual full integration

1. Same public-only N/base cohort and source-controlled base selection across classical routing and quantum branches; document any classical-first solves.
2. Synthesize reversible controlled modular multiplication/exponentiation and compiled Fourier variant on same backend and topology, with actual reset/reuse and ancilla lifecycle.
3. Obtain genuine measurement distribution from the same circuit; feed it to continued fractions and Quaspy, including cost for failures.
4. Include all classical costs, compiler costs, expected shots, depth/T/Toffoli, physical qubits and fault-tolerant architecture overhead, with competent classical baseline (Brent rho and other suitable methods).
5. No claims from mismatched cohorts or logically incomparable operation counts. Protect negative findings.

Run `python3 hardware/qrr_a31_integrated_stage_ledger.py`. It creates `results/a31_integration/a31_summary.json` and per-stage log files. No dependency installation or QPU use. A31 is a **component replay ledger**, not a claim of a finished factoring algorithm.
