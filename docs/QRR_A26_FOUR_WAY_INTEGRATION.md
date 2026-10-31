# A26 — four-track arithmetic integration audit

A26 begins with an **exact small-width arithmetic-kernel comparison**, not a claim of scalable factoring or a production-quality four-way compilation result.

Run (free, locally or in an existing CI runner):

```bash
python3 hardware/qrr_a26_fourier_kernel_audit.py --max-bits 4
```

The script exhaustively tests every input pair at widths 1–4. It compares the ideal Fourier adder (DFT / diagonal phase / inverse DFT) against exact binary addition modulo 2^n. The Fourier transform is a direct ideal simulation, not a compiled gate circuit. It also tests a narrowly defined cancel-adjacent-self-inverse-gates compiler rewrite. Its four named variants are **comparison scaffolding**: baseline binary addition, compiler, Fourier and hybrid. Only Fourier arithmetic equivalence and the independent rewrite identity are checked. An absent metric is null, not zero.

**Next integration gates (not yet implemented):** (1) construct reversible binary ripple and controlled modular-add/multiply circuits; (2) implement and verify gate-level QFT adder with controlled rotations; (3) run identical circuit compiler passes with a specified basis/coupling map and controlled routing; (4) test combinations and verify success distribution with A23/Quaspy; (5) evaluate public-first Dark Star PTP/wheel methods and full expected resource cost on identical target sets, rejecting classically solved cases; (6) compare depth, T/Toffoli, qubits, reset counts and wall time with realistic fault-tolerant overhead. Do **not** treat the direct classical DFT simulation time as quantum circuit execution cost.

A23: exact phase/recovery bridge for N=35 passed in an ideal model. A24: public wheel factors N=35, so it supplies no quantum advantage. A25: RSA physical estimates are sensitivity extrapolations, not CaMaLabs measurements. Keep all three as separate retained baselines; never add their reported gains without matched denominators and a jointly executable experiment.
