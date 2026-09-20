# TCT grid-factored shift oracle — six-round coherent arithmetic result

Date: 2026-09-19

## Scope

This records the zero-QPU compiler result for the validated, classification-exact, grid-factored/shift TCT arithmetic oracle compiled as one coherent six-round Grover circuit.

The circuit evaluates a transformed form of the frozen reduced-order FAIR-MAST-seeded TCT objective, phase-marks low-score valid parameter states, exactly uncomputes the arithmetic workspace, and applies the parameter-register diffuser. The arithmetic transformation preserves the same 8 marked scenarios among all 320 valid candidates.

This is not fusion-physics validation and is not an end-to-end quantum-speedup result.

## Validation prerequisite

The six-round compile required the passing grid-factored validation artifact. That validator established:

- classification: 320/320 valid scenarios checked, 8 marked;
- four-bit base polynomial: all 16 assignments exact;
- accumulator headroom: maximum shifted event base 23,760 < 65,536 modulus;
- full-width controlled shifts: 64/64 actual 16-bit cases passed with zero probability error;
- QFT constant-adder self-test: passed;
- overall: `all_passed=True`.

## Six-round compile

- Grover rounds: 6
- logical width: 25 qubits
- parameter bits: 9
- accumulator bits: 16
- compiled CZ: **42,756**
- compiled depth: **132,481**
- compiled size: **263,193**
- weighted interaction edges: **273**
- QPU jobs submitted: 0

## Scaling against one round

Trusted one-round reference:

- CZ: 7,126
- depth: 22,081

Naive six-times projection:

- CZ: 42,756
- depth: 132,486

Actual coherent six-round result:

- CZ ratio vs naive: **1.000000**
- depth ratio vs naive: **0.999962**

Thus the combined compile is essentially exactly linear in round count for this implementation. There is no multi-round routing/decomposition blow-up on the fully connected synthetic backend and no meaningful cross-round compiler cancellation. The five-layer depth improvement relative to naive linear scaling is negligible.

## Improvement history

### Original factorized arithmetic oracle

One round:

- CZ: 272,126
- depth: 1,083,704

Naive six-round projection:

- CZ: 1,632,756
- depth: 6,502,224

Current six-round grid-factored result relative to that projection:

- CZ reduction: **97.381%**
- depth reduction: **97.963%**

### Exact 54-term event-polynomial oracle

One round:

- CZ: 49,958
- depth: 213,221

Naive six-round projection:

- CZ: 299,748
- depth: 1,279,326

Current six-round grid-factored result relative to that projection:

- CZ reduction: **85.736%**
- depth reduction: **89.644%**

## Comparison with fixed-instance Boolean/ESOP oracle

The previously validated semantic/ESOP fixed-instance six-round oracle compiled to:

- CZ: 1,194
- depth: 5,973
- logical width: 10

The coherent arithmetic circuit is therefore about:

- **35.81x** the CZ count;
- **22.18x** the depth;
- 25 qubits instead of 10.

This difference is methodologically important. The semantic/ESOP oracle exploits the already-known marked truth table. The grid-factored arithmetic oracle coherently evaluates a structured transformed objective and uncomputes it. The latter is the relevant architecture for any future claim about coherent objective evaluation rather than precomputed state marking.

## Interpretation

The main result is not that the six-round circuit beats the classical 320-point surrogate; it does not establish that. The source objective is classically cheap, and a 320-point classical scan remains a much simpler practical computation.

The result instead closes a compiler/architecture gap that had dominated the earlier experiment: after exploiting the actual grid algebra and power-of-two event-rate structure, the honest coherent arithmetic search no longer sits in the million-depth regime. Six full Grover rounds now compile to roughly `4.3e4` CZ and `1.3e5` depth on a fully connected synthetic backend.

The next hardware-relevant test is sparse-topology routing of this validated 25-qubit six-round circuit on IBM Fez heavy-hex connectivity, with an explicitly labeled square-lattice proxy comparison if used. Any such result must be reported as best among screened patches unless an exhaustive patch audit is performed.

## Boundaries

- Zero QPU execution.
- Fully connected synthetic backend only for this result.
- Classification-exact transformed arithmetic, not pointwise-identical loss arithmetic.
- Reduced-order FAIR-MAST-seeded search model, not tokamak-physics validation.
- No error rates, timing, fidelity, reset, or fault-tolerance overhead included.
- No practical or asymptotic quantum-advantage claim.
- Classical objective evaluation remains inexpensive at this 320-state scale.
