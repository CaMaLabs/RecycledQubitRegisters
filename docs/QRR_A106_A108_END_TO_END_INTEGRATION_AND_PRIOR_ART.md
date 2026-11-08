# A106–A108 integration and published-method benchmarking gate

**Created 2026-11-04.** Status: new scripts committed, **not executed** on the Ubuntu/Qiskit workstation. No results should be reported until the commands below run.

## What is integrated now

- A97 is a complete controlled modular multiplier. A99 validated five individual A97 modular-power stages against IBM Fez's real target topology, with 3.9104% fewer native CZ operations and 3.2473% less routed depth than A87b.
- A102 through A105 implement and audit reversible modulo-N three-input sum and externally controlled XOR. A105 improved native CZ 19.2972% vs matched ripple, but required 111 vs 84 logical qubits.
- A106 is **the first actual carry-save modular multiplier**, with compute / controlled-swap / inverse-compute and a ternary partial-product tree. It has **not yet passed correctness or cost**. Its full resource cost cannot be inferred from A105.
- A107 now connects the *existing* Dark Star public odd-power base preconditioning and strict public continued-fraction factor verifier to **actual A97 recycled dynamic QPE circuits** and Qiskit Aer measurements. This is a small-N test, **not** synthetic known-order phase sampling and **not** A106.
- A108 independently gates A106 on full multiplier semantics and costs against A97 with optional T-count/T-depth obtained by synthesizing the same circuits into Clifford+T. It includes an exact width preflight to reject cases that cannot fit IBM Fez's 156 physical qubits before building the giant circuit.

## Published work: prior art and required apples-to-apples controls

| Source | Established contribution | What we have NOT done |
|---|---|---|
| Gossett, *Quantum Carry-Save Arithmetic* (1998), https://arxiv.org/abs/quant-ph/9808061 | Quantum carry-save arithmetic, avoids serial carry propagation at qubit cost | Independent implementation of full Gossett algorithm under A97/A106's interface |
| Wang et al., *Reducing T-Depth and T-Count in Quantum Multiplication Using Compressor Primitives* (GLSVLSI 2025), https://doi.org/10.1145/3716368.3735184 | Generalized compressor / Wallace tree, T-cost reductions against paper baselines | Reproduced optimized compressor library and same whole-multiplier resource comparison |
| Zhang et al., *Optimized Quantum Folding Barrett Reduction for Quantum Modular Multipliers* (Scientific Reports 2025), https://doi.org/10.1038/s41598-025-04987-1 | Reversible modular reduction via folding Barrett | Gate-accurate Barrett circuit implementation with clean quotient/scratch |

**No novelty claim.** A107/A108 are *integration and comparable-metric infrastructure*, not reimplementations of the three papers. No percentage from their papers is directly comparable to A99 or A105. Publishable comparisons require the **same function** (fully controlled modulo-N multiplication with invalid inputs unchanged and clean scratch), native basis, qubit constraint, compilation settings, benchmarks and phase/unitary semantics.

## Command: validation gates

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"

# A106 must pass full multiplier source basis audit before any integration claims.
timeout 300 "$PY" hardware/qrr_a106_csa_controlled_multiplier.py \
  --n 15 --a 2 --output results/a106_n15.json || exit 1

# A108 can provide matched fully reversible A97-vs-A106 full cost.
timeout 300 "$PY" hardware/qrr_a108_multiplier_clifford_t_parity.py \
  --n 15 --a 2 --max-qubits 156 \
  --output results/a108_n15.json || exit 1

# A107 runs genuine small-N Aer dynamic phase estimation from A97 and
# passes the observed counts to Dark Star's public strict order verifier.
timeout 300 "$PY" hardware/qrr_a107_darkstar_a97_aer_integration.py \
  --n 35 --base 8 --ell 3 --bits 12 --shots 16 \
  --output results/a107_n35.json || exit 1

# Guard-only: report A106's N2491 width and hardware fit. No giant build.
"$PY" hardware/qrr_a108_multiplier_clifford_t_parity.py \
  --n 2491 --a 8 --preflight-only \
  --output results/a108_n2491_preflight.json
```

Only after A108 passes at N=15 should N=35 native/T-accounting be attempted. `--clifford-t` is optional and can be very expensive to compile; test at N=15 first. If A106 loses badly or exceeds Fez width, explore reversible pebbling, shared scratch and compiler cost-aware mixed multipliers **before** trying to replace A97 in QPE.

## Critical research boundary

- Small semiprimes can be factored cheaply by classical trial division. An Aer factoring demonstration on N=35 gives end-to-end *functional evidence*, not a quantum speedup.
- The odd-power base transform may **raise or lower** probability and resources; report both, including negative results.
- Source exact computational-basis verification is substantive because these are permutation gates acting without phase on clean inputs, but native fidelity is a separate issue.
- T count and T depth after gate synthesis do not include magic-state factories, syndrome rounds, routing overhead or logical error correction.
- ML-KEM/LWE is a separate algorithmic cryptanalysis track: Fourier/NTT, noise manipulation and lattice attacks must not be presented as integrated into a Shor factoring circuit.
