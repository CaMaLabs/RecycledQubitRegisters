# K028 Native Arithmetic Resynthesis — experimental implementation

This package is an **implemented and locally tested reversible-Boolean-gate arithmetic prototype**, not a replacement for the Google kickmix inverse-square-root compiler yet.

## Implemented
- Exact low-width unsigned multiplication modulo `2**width` via schoolbook/ripple accumulation and carry-save column compression.
- Gate-level `X`, `CX`, `CCX` representation, executable simulator, circuit hashes, gate count, qubit count and logical dependency depth.
- Bennett compute/copy/uncompute. All work bits reset to zero; sources remain unchanged and output remains readable.
- Exhaustive verification of 3-, 4-, 5-bit arithmetic, and deterministic 512-sample verification at 6 and 8 bits.

## Run
```bash
python3 native_arithmetic.py
```

## Boundaries
- These generated circuits are **not yet exportable to the K001/Kickmix official compiler format**. No Kaggle score or official-verifier pass is claimed.
- Gate counts are not the Kaggle scoring formula, and intermediate qubit footprint does not represent optimally recycled physical qubits.
- Other proposed K028 methods (Fourier/NTT, Dark Star pruning, lattice/noise heuristics, chip placement) require native adapters and are not silently represented as implemented here.
- `clean_output()` assumes a fresh circuit with no pre-existing computed persistent outputs except source registers. Avoid applying it mid-circuit without scoping the compute region.

## Research results
Carry-save multiplication lowers gate count and temporary qubit count compared with this naïve ripple-accumulation baseline in all measured widths. It is not a validated improvement over the original K026 optimized implementation.

## Next integration step
Obtain the source and target wire/gate ABI of `competition/k001/private/...` to lower this gate IR into the competition's required format, preserve measurement/phase semantics, and compare exact official scores under the same verifier settings. Do not modify a running K026 worker.
