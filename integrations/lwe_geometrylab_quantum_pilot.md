# Experimental integration: RecycledQubitRegisters ↔ LWE_GeometryLab

**Date:** 2026-10-11. **Research direction:** Chase Lunsford (CaMaLabs), connecting his QRR/IBM Quantum dynamic-circuit and Dark Star classical-filter research with Fourier/geometric learning-with-errors (LWE) experiments. AI-assisted implementation, testing and research reporting.

**Primary reproducible LWE study:** [LWE GeometryLab QRR-informed quantum optimization pilot](https://github.com/CaMaLabs/LWE_GeometryLab/blob/main/docs/mlkem512_qrr_quantum_optimization_verified.md); successful [GitHub Actions run 38123262290](https://github.com/CaMaLabs/LWE_GeometryLab/actions/runs/38123262290).

## Established assets and honest scope

QRR's actual dynamic-register recycling for iterative quantum phase estimation and hardware-aware placement (IBM Fez/Marrakesh) does NOT directly reduce an arbitrary QAOA register: all binary search qubits are deliberately placed in a coherent superposition and must survive phase and mixing stages. Measuring/resetting those search qubits leaks/discards quantum information. Ancilla *uncomputation* can reuse scratch registers in a reversible cost oracle, but this is logically different from measuring away an entangled search variable, and no full LWE oracle has been synthesized.

QRR's useful immediate contribution is **resource transparency and the Dark Star/PTP classical-shortcut gate**: never count a quantum transformation as useful if cheap classical public-data computations already recover the desired subproblem optimum.

## Completed four-qubit real-public-objective study

On **two genuine, newly self-generated ML-KEM-512 public keys**, all 512 unknown secret coefficients and 512 unknown errors remained unknown to the algorithm. A public-only CBD3-constrained 512-variable classical baseline guessed s; **three predetermined disjoint four-coordinate tiles per key** were exhaustively scored with the entire 512-output modular equation. Matched uniform public-t targets were evaluated separately.

The ideal exact **4-qubit QAOA p=1 statevector** operated on a public 16-value diagonal cost table. Its mean probability of sampling a tile optimum was **13.88%** across six genuine-key tiles, against **6.25%** for one uniform random draw. But **every one of the six tiles already had its optimum at the original known base candidate 0000**, so the cheaper classical option `keep 0000` had **100% local-optimum success**, and QAOA had **zero public-objective improvement and no full key recovery**. The six matched uniform-target tiles were likewise already classically optimal. Exact classical enumeration costs 16 score computations per tile; QAOA training consumed **633 additional classical variational objective evaluations across the six genuine tiles** (plus cost-table compilation), before any quantum device overhead.

A full 4-bit diagonal Hamiltonian used **16 nonzero Walsh-Z coefficients**; an ideal fully-connected parity gadget decomposition has **34 CNOTs per cost layer**, EXCLUDING reversible cost-oracle synthesis, noise, routing, backend restrictions and optimizer iteration. No actual IBM QPU jobs or Qiskit hardware transpilation were performed. This is an exact simulator and an honest **negative quantum value audit**, not a quantum speedup or an ML-KEM break.

## What to try only after a successful classical subproblem

First establish *nontrivial public-only* modular-geometry search neighborhoods not already solved by classical preprocessing. Compare to exact 16-candidate enumeration and strong classical lattice baselines, count all oracle evaluations and compilation/sampling costs, and validate disjoint holdout keys before allocating QPU time. If a quantum phase-estimation primitive with valid mid-circuit measurement/reset semantics arises, QRR's phase ancilla recycling and placement software may then be useful; a QAOA coherent candidate register is not that primitive.

This integration is concept-level and references LWE_GeometryLab code; it does not modify QRR's quantum algorithms, claim undocumented hardware runs, or incorporate proprietary/private key material. Scientific credits: Chase Lunsford (CaMaLabs), AI-assisted software/research audit.
