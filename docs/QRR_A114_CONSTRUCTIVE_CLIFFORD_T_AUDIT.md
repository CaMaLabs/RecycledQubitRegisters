# A114 — Constructive exact Clifford+T resource audit

**Status:** Source committed; awaiting execution on Ubuntu.

## Motivation

A113 finished **30/30 IBM Fez local-target routing wins**, with A110 reducing matched native two-qubit gates by 11.6784% weighted and routed depth by 10.2575% weighted across five N2491 modular-power stages, two layouts and three seeds. These are compiler-stage resource metrics, not physical execution or complete QPE.

A114 asks whether A110's mathematically exact gate cancellation also saves T gates in an explicitly defined exact Clifford+T implementation.

## Explicit synthesis assumptions

- Every k-controlled X is decomposed via **k−2 additional clean reusable ancillas** and **2k−3 Toffoli gates** for k>=2 (ordinary CX/X for k=1/0). Open controls are implemented via Clifford X conjugations.
- Each Toffoli is expanded with Qiskit's standard CCXGate definition and the script asserts **7 T/Tdg and 6 CX**, not just a heuristic weighting.
- Controlled SWAP is synthesized exactly as CX–Toffoli–CX.
- A114 streams the exact decomposition operations through a ledger to avoid holding huge expanded circuits in memory.
- The T-layer scheduler synchronizes dependencies across CX operations; its T-depth is a **conservative realizable schedule for this fixed decomposition**, **not** a globally optimal T-depth.
- The additional ancillas are separately reported and included in the constructed logical qubit count.

This is an **explicit valid construction**, NOT minimum theoretical T-count, physical error-corrected qubits, magic-state factory cost, or surface-code runtime. The ancilla budget need not equal the untranspiled architecture's qubit count. All potential gains are relative to this identical chosen decomposition on both circuits.

## Runs

Start with N35, A8, exhaustive 128 input/control basis checks per architecture:

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 300 "$PY" hardware/qrr_a114_clifford_t_resource_audit.py \
 --n 35 --a 8 \
 --output results/a114_n35_clifford_t_resource_audit.json
echo "EXIT STATUS: $?"
```

Only after the N35 test passes, use N2491, power8 with algebraic exactness of the source rewrite and no exhaustive large basis simulation:

```bash
timeout 600 "$PY" hardware/qrr_a114_clifford_t_resource_audit.py \
 --n 2491 --a 8 --skip-basis \
 --output results/a114_n2491_p8_clifford_t_resource_audit.json
```

## Promotion gate

Record independently: T-count, fixed-construction T-depth upper bound, constructed qubits, CX, and the source rewrite gate counts. Never claim surface code physical resource or cryptographic factoring gains from this alone. If N35 passes and N2491 improves T-count and T-depth without increasing constructed qubits, continue to the remaining N2491 power stages.
