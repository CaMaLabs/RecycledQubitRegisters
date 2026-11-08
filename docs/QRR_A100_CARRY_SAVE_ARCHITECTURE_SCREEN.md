# A100 — Reversible carry-save architecture screen

**Implementation:** `hardware/qrr_a100_carry_save_reversible_screen.py`

**Status:** Script committed, awaits Qiskit execution on the Ubuntu workstation. No numerical win is claimed.

## Motivation

A99 confirmed that adaptive A97 outperforms A87b in all five tested IBM Fez target-routed modular-power stages, with 3.9104% fewer native two-qubit operations relative to A87b; the absolute costs remain hundreds of thousands of two-qubit gates per stage. Incremental comparator optimization is not sufficient.

A larger candidate is to postpone carry propagation by compressing three addends into two. For input bits `a_j,b_j,c_j`, the **reversible** 3:2 compressor writes into clean scratch:

```text
t_j     = a_j XOR b_j
sum_j   = t_j XOR c_j
carry_j = (a_j AND b_j) XOR (t_j AND c_j)
```

For each bit `a_j + b_j + c_j = sum_j + 2*carry_j`; therefore for `w` bits:

```text
a+b+c = S + 2*C (mod 2^w)
```

The circuit preserves all three inputs, computes S and C, performs only two carry-propagating variable additions into a clean output, and **uncomputes** both temporary registers. The comparator is three successive variable ripple additions into the same output. Both should realize the same `|a,b,c,0,clean> -> |a,b,c,(a+b+c) mod 2^w,clean>` mapping.

## Why this might still lose

The clean reversible carry-save implementation requires `2w-1` *additional* scratch qubits: `4w` baseline vs. `6w-1` candidate. Full cleanup doubles the compressor's compute/uncompute overhead. It also uses two ripple adders rather than zero. Whether this saves CX gates or depth must be established by actual full-circuit compilation and source-gate semantics checks. **No advantage for 12-bit multiplication, modular reduction modulo N, or RSA factoring is implied.**

## Validation gates

- Exhaustive source-basis check of all triples for `w<=4`; seeded random/edge-case triples for larger widths.
- Compare full native `u/cx` transpiled gate counts, depth, width and scratch cleanup at matched optimization level/seed.
- Promote only if exact and the qubit-vs-gate resource tradeoff is beneficial.
- If the baseline beats carry save, try batched partial-product compression or qubit-recycled compressor pipelines, rather than silently dropping scratch costs.
- Only then integrate modular reduction and a clean controlled multiplier, followed by phase tests and IBM backend target routing.

## Run

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 120 "$PY" hardware/qrr_a100_carry_save_reversible_screen.py \
  --width 4 --output results/a100_w4.json || exit 1
timeout 180 "$PY" hardware/qrr_a100_carry_save_reversible_screen.py \
  --width 12 --probes 128 --output results/a100_w12.json
echo "EXIT STATUS: $?"
```

No paid IBM runtime, no QPU submissions.
