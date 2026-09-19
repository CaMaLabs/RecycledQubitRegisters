# TCT grid-factored shift oracle result

Date: 2026-09-19

## Scope

This records the zero-QPU compiler result for the grid-factored/controlled-shift implementation of the FAIR-MAST-seeded TCT reduced-order arithmetic oracle.

The construction returns to the reduced-order formula

`L = A * event_mult * (1-bias) * (1-r*boost) + B*bias + C*false_mult`

and exploits structure in the frozen parameter grids instead of synthesizing the 64 rounded event-table values independently.

This remains a reduced-order surrogate/compiler result. It is not fusion-physics validation and is not evidence of end-to-end quantum advantage.

## Encoding result

- recovered reachable fraction: `38/59`
- transformed scale: `qscale=1`
- threshold: `1632`
- maximum score: `23817`
- accumulator: `16` qubits
- parameter register: `9` qubits
- logical width: `25` qubits
- classification exact over all 320 valid scenarios: `True`
- controlled-shift primitive self-test: `True`
- maximum absolute reconstructed-loss error: `0.0316624`

Grid factors:

- bias factors: `{0: 18, 1: 16, 2: 15, 3: 13}`
- boost factors: `{0: 165, 1: 146, 2: 127, 3: 108}`
- event numerators: `{0: 1, 1: 2, 2: 4, 3: 8}`

The bias/boost event base collapses to only 9 nonzero Boolean monomials:

- degree 0: 1
- degree 1: 4
- degree 2: 4

No degree-3 or higher terms remain.

## Compiler result

Fully connected synthetic backend, optimization level 1, transpiler seed 8776:

| Circuit | CZ | Depth | Size | Weighted edges |
| --- | ---: | ---: | ---: | ---: |
| grid-factored shift event forward | 1,400 | 3,675 | 8,541 | 220 |
| full one-round grid-factored shift oracle | **7,126** | **22,081** | **43,888** | 273 |

## Improvement

Relative to the exact 54-monomial event-polynomial oracle:

- full CZ ratio: `0.142640`
- CZ reduction: **85.74%**
- full depth ratio: `0.103559`
- depth reduction: **89.64%**

Relative to the original 64-pattern arithmetic oracle:

- full CZ ratio: `0.026186`
- CZ reduction: **97.38%**
- full depth ratio: `0.020375`
- depth reduction: **97.96%**

The original one-round arithmetic baseline was 272,126 CZ / depth 1,083,704. The structured grid-factored implementation is 7,126 CZ / depth 22,081.

## Interpretation

The dominant cost in the original arithmetic oracle was not inherent to threshold comparison or Grover diffusion. It came from representing a simple multiplicative reduced-order event term as 64 independent equality-selected constants.

Exploiting the actual grid algebra removes that expansion:

1. the bias and boost codebooks reduce to affine two-bit factors;
2. their product becomes a degree-2 four-bit polynomial with only nine nonzero terms;
3. the event-rate grid is exactly a power-of-two sequence after denominator removal, so event scaling becomes reversible controlled shifts rather than another lookup/table polynomial.

This is substantially closer to an honest structured arithmetic oracle than the fixed-instance Boolean/ESOP oracle because it evaluates the reduced-order objective from parameter values rather than phase-marking the already-known eight solutions.

However, the transformed arithmetic is specialized to these frozen codebooks and the classification target. It preserves the exact eight-state classification, not every previously rounded intermediate event-table integer. The maximum reconstructed-loss error is 0.0316624 in the source loss units.

## Remaining validation and next step

Before using this as the trusted coherent-arithmetic baseline for six Grover rounds or sparse-topology routing:

1. validate the controlled shifts at the actual 16-bit accumulator width across every reachable event-base value and all four event codes;
2. exhaustively validate the nine-term base polynomial over all 16 bias/boost assignments;
3. retain the existing all-320 classification/comparator/overflow checks;
4. then compile the full six-round circuit and measure scaling.

## Boundaries

- Zero QPU jobs.
- Reduced-order FAIR-MAST-seeded objective only.
- Specialized frozen parameter grids/codebooks.
- Exact marked-set classification over 320 valid scenarios, not exact preservation of all floating-point losses.
- No fault-tolerance, error-rate, timing, or QPU-fidelity model.
- No end-to-end quantum-speedup claim.
- No fusion-physics validation.
