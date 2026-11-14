# K145 — cubic phase tensor zero-ancilla proof of concept

## Research origin (2026-11-14)
- Khoruzhii, Gelß, Pokutta, *Tensor Decomposition for Non-Clifford Gate Minimization*, revised Oct 26 2026: https://arxiv.org/abs/2602.15285
- Original full CP-decomposition C++ implementation: https://github.com/ZIB-IOL/polytof
- Additional relevant inverse-square-root-inspired technique from Gu, Kemeny, Yelin, Lukin (Oct 2026): https://arxiv.org/abs/2610.22367 and https://github.com/andigu/uncompute. That Coulomb circuit has 142 qubits and different task precision; it is not a drop-in for 62q Helios.

## What actually is implemented
`k145_cubic_tensor.py`: a **small, self-contained cubic polynomial basis-change optimizer inspired by Polytof**, **NOT** the upstream Polytof CP decomposition (SGE/FGS/BCO).

It finds maximal contiguous unconditional regions containing only **CX, Z, CZ, CCZ**, represents the quantum phase exactly as a GF(2) polynomial, greedily looks for free CNOT basis changes that reduce the number of cubic terms, and reconstructs the entire exact region. Every candidate undergoes exact symbolic equivalence checking of both the complete phase and all affine output registers.

The synthetic self-test includes an exact two-CCZ-to-one-CCZ reduction, with no new qubits. **An improvement on a synthetic case is not an improvement on Helios.**

### Why distinct from previous work
K096/K135–K138 focused on nonlinear reversible **outputs** and CCX patterns under local truth-table/ANF constraints. K143 used the **quadratic** phase polynomial with Clifford CZ/CX only, giving no direct score delta. K145 checks **cubic CCZ phase tensors**, with zero new qubits.

### Limitations / fail fast
- No HMR, resets, conditions, X, or CCX may cross the optimized region.
- This intentionally restrictive gate library might have **zero eligible Helios regions**; if so, record a negative applicability result. Do not just increase caps or create another static scan.
- Actual `polytof` can optimize more complex bounded {H,CNOT,Toffoli} circuits, but its decomposition is not a drop-in to Kickmix; CCX-to-CCZ conjugations and H boundaries require exact semantic proof and phase preservation.
- If a native score reduction is found, a candidate must still pass the exact full-domain private official verifier, with the required zero scratch and phase accuracy. No Kaggle submission.
- Score `Q*(mean executed Toffoli-like + T-equivalent/4)`; one always-executed CCZ removed at 62q predicts ~62 point improvement assuming everything else unchanged.

### Run on Ubuntu
```bash
cd ~/quantum-a26-check
mkdir -p competition/k145
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/2552c34c0ecbce64f21d299bcf9449228538fc96/competition/k145/k145_cubic_tensor.py -o competition/k145/k145_cubic_tensor.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k145/k145_cubic_tensor.py --candidate competition/k145/results/candidate.kmx
```

Outputs `competition/k145/results/cubic_tensor_report.json`. A candidate is emitted **only** if a strict local scored-CCZ reduction and exact operator proof hold.

If `improving_windows=0`, record that the restrictive compiler representation does not yield a win; do not claim Polytof itself was comprehensively tested.
