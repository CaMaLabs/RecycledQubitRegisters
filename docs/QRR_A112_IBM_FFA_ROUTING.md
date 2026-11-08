# A112 — Matched IBM Fez target routing: A97 vs A110

**Status:** committed; independent user-machine run required.

## Scientific goal

A110 canceled 51 commuting gate pairs, reducing the complete N35 multiplier from 12,287 to 10,527 local CX and from 20,957 to 17,885 depth (18 logical qubits). A111 confirmed the improvement in full N35 dynamic recycled QPE: 24,571 -> 21,051 CX and 41,906 -> 35,681 depth, identical observed ideal Aer phase histograms over 48 shots per architecture.

A112 tests whether this savings survives the **real IBM device coupling graph and native gate target** at five more demanding N2491 modular powers (8, 64, 2448, 2217, 1051). This is a hardware-aware **local transpilation** benchmark, **not a hardware execution**. No QPU jobs, runtime session, sampler or estimator invocation.

Implementation derives directly from A99's proven IBM target routing code. Both candidates use identical connected physical initial layout, device target, level and transpiler seed. Checkpoint results after each candidate and process one modular-power pair per invocation by default. Includes sampled computational-basis modular-multiplier semantic verification; A110's rewrite is restricted to proven commuting classical-permutation involutions, which should also preserve phase coherently.

## Run first stage

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 600 "$PY" hardware/qrr_a112_ibm_commutation_routing.py \
 --backend-name ibm_fez --n 2491 --base 8 \
 --max-new-powers 1 \
 --output results/a112_n2491_ibm_fez.json
echo "EXIT STATUS: $?"
```

Repeat the command for subsequent stages, or use a loop, preserving the output checkpoint and the same backend/layout/seed. A complete checkpoint will compare stage-summed native two-qubit gates and depths; sums are **not** the depth or gate count of a full N2491 phase-estimation circuit.

## Cautions

Do not infer execution fidelity, fault-tolerant requirements, global RSA cryptanalysis, or ML-KEM vulnerability from this. Dynamic hardware QPE is not attempted. A stale/missing IBM account credential or backend may prevent device metadata access. A112 is a route-aware compile experiment only.
