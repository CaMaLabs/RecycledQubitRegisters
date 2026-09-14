# Gate-level modular multiplication synthesis

This benchmark adds an explicit reversible-gate decomposition beneath the toy RSA/Shor simulations.

For each self-generated semiprime `N` and coprime base `a`, every controlled modular-multiplication power required by `m = 2n`-bit QPE is synthesized as an exact permutation on the `n`-qubit work register:

`|y> -> |a^(2^k) y mod N>` for `y < N`, with states `y >= N` left unchanged.

The synthesis path is:

`permutation cycles -> basis-state transpositions -> Gray-path adjacent basis swaps -> MCX -> Toffoli chain`

Each resulting modular permutation is exhaustively validated over all work-register basis states. The clean-ancilla MCX-to-Toffoli chain is also independently truth-table validated for every control pattern.

## 6-9 bit sweep

Five cases were run at each work-register size.

| N bits | Trials | Distinct N | Wide width incl. arithmetic ancillas | Recycled width incl. arithmetic ancillas | Median adjacent swaps | Median Toffoli | Toffoli range | Validated |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 6 | 5 | 1 | 22 | **11** | 1,152 | 10,368 | 1,548-10,476 | yes |
| 7 | 5 | 2 | 26 | **13** | 4,883 | 53,713 | 52,569-54,043 | yes |
| 8 | 5 | 1 | 30 | **15** | 12,292 | 159,796 | 158,912-159,939 | yes |
| 9 | 5 | 2 | 34 | **17** | 34,333 | 514,995 | 512,700-725,970 | yes |

All 20 cases passed both the modular-permutation validation and the MCX truth-table validation.

The 6- and 8-bit balanced toy-key generators have very few possible distinct prime pairs, so repeated moduli are expected at those sizes. The 7- and 9-bit cases include multiple generated moduli.

## Width accounting changes once arithmetic ancillas are included

The earlier phase-register-only model counted:

- wide: `n` work + `m=2n` phase = `3n` qubits,
- recycled: `n` work + 1 phase = `n+1` qubits.

This gate synthesis uses a clean-ancilla linear MCX construction. A controlled adjacent basis-state swap has `n` controls: the external phase/control qubit plus `n-1` work-register pattern controls. The MCX therefore uses `n-2` reusable clean ancillas and `2n-3` Toffolis.

Including those arithmetic ancillas gives:

- wide: `n + 2n + (n-2) = 4n-2`,
- recycled: `n + 1 + (n-2) = 2n-1`.

For this particular synthesis model, the simultaneous-width reduction is therefore exactly **2x** across the tested sizes. This is more conservative and more meaningful than the earlier phase-register-only width ratio.

## What recycling does and does not save

The controlled modular multipliers act on the same work register in both architectures, so the arithmetic Toffoli burden is essentially shared. Recycling primarily removes the need to keep the full `2n`-qubit phase register coherent at once.

The wide implementation additionally needs the inverse-QFT two-qubit phase-rotation network. The recycled implementation replaces those quantum-quantum inverse-QFT interactions with mid-circuit measurement/reset and classically conditioned single-qubit phase corrections.

This means the main demonstrated gate-level benefit here is **simultaneous quantum width**, not an arithmetic-gate-count reduction.

## Important limitation: deliberately generic synthesis

The permutation decomposition is exact, but it is intentionally generic and highly unoptimized. It synthesizes arbitrary modular-multiplication permutations through basis-state transpositions rather than using a specialized reversible modular adder/multiplier such as an optimized ripple-carry, carry-lookahead, Fourier, or windowed arithmetic construction.

Accordingly, the Toffoli/CNOT/T counts are best interpreted as a reproducible exact-synthesis reference / upper-bound-style benchmark, **not** as competitive resource estimates for large RSA Shor implementations.

For reporting only, each Toffoli is also converted to the conventional `6 CNOT + 7 T` accounting. The repository preserves native Toffoli counts as the primary metric.

## Reproduce

```bash
python simulation/rsa_gate_level_modmul.py \
  --bits 6 7 8 9 \
  --trials 5 \
  --seed 8776 \
  --outdir results/rsa_gate_level
```

The script also generates `gate_level_powers.csv` and `gate_level_results.json` locally for detailed per-QPE-power inspection. The committed `gate_level_summary.csv` and `gate_level_trials.csv` contain the reference sweep summarized above.

See the complementary end-to-end factoring/decryption tests in [`../rsa_shor/RESULTS.md`](../rsa_shor/RESULTS.md). Those establish Shor semantics; this benchmark establishes an explicit reversible gate decomposition and realistic arithmetic-ancilla width accounting for the modular operator.
