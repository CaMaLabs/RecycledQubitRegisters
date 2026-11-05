# A106: First complete controlled modular multiplier using carry-save

**Status: first N=15/A=2 run failed; inverse-XOR cleanup defect identified and patched at commit d880ee9; rerun pending.** This is an architectural trial, not a claim that carry-save is the best factoring implementation.

## Evidence and goal

A105 locally routed a fully cleaned, externally controlled three-input modulo-2491 XOR operation onto IBM Fez: 209,735 baseline CZ gates versus 169,262 carry-save CZ gates (19.30% reduction), 397,233 versus 301,330 depth levels (24.14% reduction), but 84 versus 111 logical qubits. The next gate is whether this technique helps an **actual controlled modular multiplier**, not an isolated sum.

## Exact reversible construction

For N odd and gcd(A,N)=1, the target contract is:

`|c,x,0,clean> -> |c,(A*x mod N if c and x<N else x),0,clean>`

The input operand is a w-bit register; invalid x>=N remains unchanged. The circuit implements the same reversible multiply-by-A-on-valid-domain permutation as A97:

1. Compute a clean enable bit `active = control AND [x<N]`.
2. Group the constant-weighted binary partial products `(A*2^j mod N) * x_j * active` into ternary groups. Each group accumulates via the fully reversible A102 carry-save `(u+v+w) mod N` kernel into a separate, clean w-bit node.
3. Reuse the **same kernel workspace** across every tree node. Uncompute every temporary operand copied into the kernel.
4. XOR the root residue into an initially zero result register, reverse all internal tree nodes, and leave no partial-product garbage.
5. Controlled-swap x and y, then run the **same clean tree** with `-A^{-1} mod N` to erase the old x value held in y. Clear the active flag.

This makes an exact, quantum-reversible gate circuit composed of ordinary X/CX/CCX/MCX/CSWAP primitives. It does not rely on an oracle, classical lookup table, or measurement.

**Important design tradeoff:** A102 is itself a completely clean modular-sum kernel. Its compute/uncompute cost is repeated at every ternary node. This first construction may have much **more** CX cost or depth than A97 even though its modular-sum primitive is faster. Its ternary-tree nodes and large shared kernel also increase logical qubit count; N=2491 can exceed IBM Fez's 156 qubits. This is an explicit feasibility/falsification experiment.

## Verification

- Exhaustively check full source-basis controlled multipliers for N=15 and N=35, including control off, invalid x, clean ancillas, and clean y.
- Compile the **complete** carry-save controlled multiplier and A97 baseline to the same local u/cx basis, level, and seed; compare total CX count, circuit depth and logical qubits. This is not a sum of subroutine costs.
- For larger N use bounded source tests and width screening before expensive compilation; do not imply full hardware viability just from logical correctness.
- A success requires a complete multiplier win on a meaningful native metric with an acceptable hardware footprint. Otherwise, report a genuine negative result and consider pebbling, ancilla recycling, or specialized constant-modular arithmetic.

## Initial run

```bash
cd ~/quantum-a26-check && git pull --ff-only
PY="$HOME/ibm-6c2q-venv/bin/python"
timeout 180 "$PY" hardware/qrr_a106_csa_controlled_multiplier.py \
  --n 15 --a 2 --output results/a106_n15.json || exit 1
timeout 300 "$PY" hardware/qrr_a106_csa_controlled_multiplier.py \
  --n 35 --a 8 --output results/a106_n35.json
echo "EXIT STATUS: $?"
```

No paid runtime or IBM hardware jobs.

## N=15 regression and correction (2026-11-04)

The first user-run N=15, A=2 circuit produced `actual=485` instead of `expected=5` for control=1, x=1. Binary output decoding showed the product register had been set to 15 rather than cleaned. Root cause: we had ported A97's **negative inverse modular-adder cleanup** into a **bitwise-XOR result accumulator**. These are not interchangeable operations.

After the controlled swap, the old x value is in y and the new x contains A*x modulo N. For XOR cleanup, the second tree must calculate **positive** `A^-1 * new_x mod N` and XOR that with y, leaving y=0. The code now uses `accumulate(inverse)`, rather than `accumulate(-inverse)`, and includes a fail-fast algebraic regression over all valid x.

This fixes the identified mathematical sign error. It **does not constitute a successful full-circuit test**; rerun exhaustive source-basis verification on the workstation before interpreting any cost measurements or moving to larger N.
