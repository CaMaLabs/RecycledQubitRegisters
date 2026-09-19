# TCT reversible arithmetic oracle — component cost breakdown

Date: 2026-09-19

## Scope

This records a zero-QPU compiler decomposition of the classification-exact, factorized fixed-point TCT reversible arithmetic oracle. The purpose is to identify the dominant implementation cost before redesigning the oracle.

The arithmetic oracle evaluates the reduced-order Mirnov/toroidal objective coherently, compares the score with the frozen threshold, phase-marks valid low-score states, and uncomputes the score. This is distinct from the much cheaper fixed-instance Boolean/ESOP oracle.

## Configuration

- parameter bits: 9
- comparison-safe accumulator bits: 15
- logical width: 24 qubits
- factorized fixed-point threshold: 767
- modular comparison offset: 32000
- event conditioned constants: 64
- bias conditioned constants: 1
- false-trigger conditioned constants: 4
- optimization level: 1
- transpiler seed: 8776
- fully connected synthetic backend
- QPU jobs: 0

## Compiled component costs

| Component | CZ | Depth | Size | Weighted edges |
| --- | ---: | ---: | ---: | ---: |
| QFT + inverse QFT only | 420 | 545 | 2,717 | 105 |
| offset forward | 462 | 559 | 2,870 | 105 |
| event forward | **134,560** | **535,394** | **826,229** | 210 |
| bias forward | 552 | 1,002 | 3,444 | 136 |
| false-trigger forward | 1,662 | 5,865 | 10,246 | 153 |
| score forward all | **135,850** | **541,005** | **834,185** | 258 |
| valid-low-score phase mark | 100 | 446 | 623 | 6 |
| parameter diffuser | 42 | 168 | 358 | 15 |
| full one round | **272,126** | **1,083,704** | **1,670,950** | 258 |

## Bottleneck

The event block is the dominant cost by an overwhelming margin.

- `event_forward / score_forward_all = 134560 / 135850 ≈ 99.05%` of forward-score CZ.
- Forward plus reverse event evaluation contributes approximately `2 × 134560 / 272126 ≈ 98.90%` of full one-round CZ.
- The phase mark is only 100 CZ.
- The diffuser is only 42 CZ.
- QFT/IQFT overhead is small relative to the event block.

The current event implementation uses 64 code-conditioned constants over the 2-bit event-rate, 2-bit standing-bias, and 2-bit boost registers. Each selected constant becomes controlled phase additions across the 15-qubit QFT accumulator. This equality-pattern implementation therefore pays for many high-control operations and then pays essentially the same cost again during uncomputation.

## Interpretation

This result rules out the comparator, diffuser, validity mark, and QFT shells as primary optimization targets. The next redesign should focus on the event function

`A * event_mult * (1-bias) * (1-reachable*boost)`

and exploit its algebraic structure rather than enumerating all 64 code combinations.

The underlying parameter grids have substantial structure:

- event multiplier: `[0.25, 0.5, 1.0, 2.0]`, a power-of-two progression;
- `1-bias` for bias `[0.10, 0.20, 0.25, 0.35]` equals `[18,16,15,13]/20`, i.e. `18 - 2*b0 - 3*b1` over the 2-bit bias code;
- the 3 ms reachable fraction is `38/59` from 38 latency-reachable events out of 59 reviewed events;
- boost `[0.25,0.40,0.55,0.70] = [5,8,11,14]/20`, so the attenuation numerator `1180 - 38*boost_num` is `[990,876,762,648] = 990 - 114*g0 - 228*g1` over the 2-bit boost code.

This makes an algebraically factored implementation plausible. Before implementing a full reversible multiplier, the next controlled experiment is to apply exact Möbius/multilinear synthesis to the 6-bit event-value function. That preserves the exact 64 integer event outputs while replacing equality-pattern selects with monomial controls. The resulting control-degree distribution and compiled cost will determine whether this structured intermediate is sufficient or whether a true shift/add multiplier is warranted.

## Claim boundaries

- Zero QPU jobs.
- Reduced-order FAIR-MAST-seeded objective only.
- Compiler cost decomposition, not evidence of quantum advantage.
- No fusion-physics validation.
- The fixed-instance Boolean/ESOP oracle remains much cheaper, but it is not a scalable coherent-surrogate implementation.
