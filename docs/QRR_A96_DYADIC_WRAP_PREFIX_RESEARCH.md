# A96 — Dyadic interval-prefix synthesis of modular wrap flags

**Status:** Implemented; awaiting Ubuntu/Qiskit execution. No A96 speedup has been measured.

## Evidence motivating the experiment

A95 compiled A87b conditional comparators at N=2491 to 228 CX (threshold 1245) and 270 CX (threshold 2490), versus A84 at 530 and 656 CX, respectively. The A94 IBM Fez local-target holdouts demonstrated 5/5 A87b routed-stage wins and 15.74% combined native two-qubit-gate reduction. However, the A95 representative two-qubit fault-event proxies remain above 1100 per tested A87b stage, so the architecture is not yet viable on uncorrected hardware.

## Mathematical transformation

A87b constructs the modular-addition wrap flag using

```
wrap ^= [x >= N-k]
wrap ^= [x >= N]
```

Because `[x>=a] XOR [x>=b] = [a<=x<b]` for `a<b`, the wrap flag is exactly the half-open interval predicate

```
wrap ^= [N-k <= x < N]
```

A96 decomposes this integer interval into a minimal partition of **aligned binary blocks**. A block of size `2^t` is recognized by comparing only the `w-t` high bits of the register. The blocks are mutually exclusive, so XORing their Boolean predicates yields precisely the interval indicator, with no added ancilla.

The same interval generator is applied during initialization and during control-off wrap cleanup. The control-on output-cleanup predicate remains A87b's direct threshold comparator, so this is a focused test of wrap interval sharing, not a completely new modular arithmetic system.

## Tests and promotion requirements

1. Exhaustively verify every half-open interval (including the upper endpoint `2^w`) for widths 2 and 3, both conditional-control states.
2. Exhaustively verify controlled modular constant addition, including out-of-domain states and zeroed ancillas, for N=15, N=35 and the target modulus.
3. Exhaustively verify controlled modular multiplication of all `2^(w+1)` control/work inputs for N=35 and N=247, against A87b under identical Qiskit optimization level and seed.
4. Compare qubit counts, native CX count and compiled depth. Require **no additional qubits and exact reversible correctness**. Negative results are recorded as such.
5. If it wins locally, profile the complete powers at N=2491, then independently seeded ideal Aer phase measurements and real-IBM-target **local-only** routing.

**Limitations:** Basis checks alone do not prove phase fidelity; ideal CX gates are not equivalent to native CZ cost; no QPU execution or physically calibrated factoring-success probability. A96 cannot be claimed as an improvement until the Ubuntu benchmark prints successful checks and lower counts.

## Run

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 120 "$PY" hardware/qrr_a96_interval_prefix_multiplier.py --n 35 --k 8 --output results/a96_n35.json || exit 1
timeout 180 "$PY" hardware/qrr_a96_interval_prefix_multiplier.py --n 247 --k 8 --output results/a96_n247.json
echo "EXIT STATUS: $?"
```
