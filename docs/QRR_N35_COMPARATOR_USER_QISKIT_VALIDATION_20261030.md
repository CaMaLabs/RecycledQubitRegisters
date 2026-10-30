# N35 comparator A/B validation receipt — 2026-10-30

Research lead Chase Lunsford / CaMaLabs.

User-provided terminal output from local Ubuntu `ibm-6c2q-venv`; independently executed in user's Qiskit environment, not rerun by assistant. GitHub SHA of corrected source: a096c931561320c48f9ecb14d76939377a4a652a.

- `python hardware/qrr_n35_validity_comparator_transplant.py --qiskit` completed. CPU 128, Qiskit gate-interpreter 256 baseline + 256 candidate cases; both exactly phase +1. Baseline counts CX14 CCX11 X2; candidate CX13 CCX11 X0.
- `python hardware/qrr_n35_comparator_ab.py --qiskit` completed: full Qiskit Statevector 128 tests each. Factored (11 wires, 4 scratch): CX12 CCX9. Ripple (13 wires, 6 scratch): CX15 CCX10. Both PASS exact phase +1.
- No full N35 multiplier swap, no native Fez compilation and no QPU time used.
- NOTE: standalone comparator baseline and controlled source baseline differ; never conflate their resource deltas.
- Next: transplant only threshold35 validity check in actual controlled multipliers, repeat 128 control×input exhaustive exact operator check for each public power; then four-seed read-only Fez cost comparison and record failures.
