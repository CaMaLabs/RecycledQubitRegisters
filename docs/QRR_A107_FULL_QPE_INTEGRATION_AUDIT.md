# A107 — Integration gate: adaptive arithmetic to full QPE

**Status:** Implementation committed; execution results are not yet available.

This experiment extends A89/A88's genuine recycled-phase-qubit dynamic quantum phase estimation with the A97 per-constant adaptive controlled modular multiplier. It compares the **entire transpiled QPE circuits** (A87b vs A97), obtains independently seeded ideal Aer MPS measurement histograms, and feeds those frequencies through the *same* continued-fraction candidate-order/factor verifier.

The source-basis tests verify every distinct stage over all control and input bit patterns at N=15 or 35. The dynamic phase circuit is transpiled to identical `u/cx` basis, seed and optimization level; qubit requirements match because both multipliers use `2w+6` logical qubits.

**Important honesty boundary:** A107 is **not** the total historic Dark Star research stack. It doesn't embed periodic-prime tables, recursive Fourier pruning, older classical precomputation, LWE/ML-KEM cryptanalysis, A106 carry-save multiplication or fault-tolerant resource scheduling. Those remain independent until explicitly integrated and measured. Classical continued-fraction order recovery *is* integrated. A107 is a real complete QPE circuit only for the small supported modulus, not a physical quantum attack on secure RSA.

## Reproduction

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 300 "$PY" hardware/qrr_a107_adaptive_end_to_end_qpe.py \
  --n 15 --base 2 --bits 8 --shots-per-seed 32 --seeds 3 \
  --output results/a107_n15_qpe.json
```

Optional A106 independent multiplier check:

```bash
timeout 240 "$PY" hardware/qrr_a106_csa_controlled_multiplier.py \
  --n 15 --a 2 --skip-native --output results/a106_n15_source_only.json
```

Do not promote A106 to the quantum phase circuit until its exact source-basis semantics, clean ancillas, hardware width and full native cost are established. In particular, a reversible XOR cleanup after a controlled swap needs `+a^{-1}`, not `-a^{-1}`. A106's current branch code includes that sign correction but still requires an independent run.

## Literature comparison requirements

The next resource ledger must compare equivalent arithmetic functions, **all ancilla cleanup**, logical and physical qubits, native 2Q gates/depth, and fault-tolerant T/Toffoli count/depth. Historical carry-save, compressor-tree, Barrett-reduction and Gidney-style modular arithmetic are relevant prior art. Do not infer novelty solely because these experimental implementations win against our earlier local baseline.

This repo's benchmark outputs and explicitly recorded statuses are evidence of **experiment results**, not a proof that a strong RSA or ML-KEM instance has been broken.
