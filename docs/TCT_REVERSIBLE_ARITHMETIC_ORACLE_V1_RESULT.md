# TCT reversible arithmetic oracle v1 result

Date: 2026-09-18

## Scope

This records the first zero-QPU compiler probe of a coherent reversible arithmetic oracle for the reduced-order FAIR-MAST-seeded TCT search objective.

Unlike the earlier table oracle, this circuit computes the fixed-point TCT loss function coherently, compares the result against the frozen low-loss threshold, phase-marks qualifying valid parameter codes, and uncomputes the arithmetic workspace.

## Arithmetic specification

The source fusion specification reproduced the frozen eight marked scenarios exactly:

- valid scenarios: 320
- marked scenarios: 8
- parameter register: 9 qubits
- source accumulator width: 14 qubits
- factorized fixed-point scale: 10
- factorized threshold: 767
- classification exact: true
- QFT constant-adder self-test: true
- comparison-safe accumulator width: 15 qubits
- total logical width: 24 qubits
- conditioned constants: 64 event, 1 bias, 4 false-trigger

The direct fusion specification used threshold 768, while the factorized integer implementation uses 767 because its term-by-term rounding path is slightly different. Both reproduce the same frozen eight-state marked set exactly.

## One-round compiler probe

Exact-width fully connected synthetic backend, zero QPU:

- logical width: 24
- weighted logical edges: 258
- total 2Q interaction weight: 272,126
- native CZ: 272,126
- compiled depth: 1,083,704
- compiled size: 1,670,950
- compile time: 5.563 s

## Comparison with the table oracle

The one-round 9-qubit table-oracle probe used:

- 2,268 CZ
- depth 9,310

Therefore the coherent arithmetic oracle costs approximately:

- 119.99x as many CZ gates per Grover round
- 116.40x as much compiled depth per Grover round
- 24 logical qubits instead of 9

The idealized search model for the 320-scenario / 8-marked problem requires 6 Grover iterations versus 35.6667 expected random-without-replacement classical candidate evaluations, an oracle-query ratio of 5.9444x.

The measured arithmetic-oracle overhead is therefore far larger than the idealized query reduction at this problem size. Even before sparse-topology routing, QPU errors, fault tolerance, state preparation, measurement, or wall-clock execution are included, this implementation does not support an end-to-end quantum advantage claim.

A naive linear six-round projection would be approximately 1,632,756 CZ and depth 6,502,224 on the same fully connected logical probe. A six-round arithmetic compile is not justified before reducing the oracle cost substantially.

## Interpretation

This is a useful negative result rather than a failed experiment:

1. The TCT objective can be encoded coherently and exactly with a compact 9-bit parameter register and 15-bit comparison-safe accumulator.
2. The straightforward QFT constant-addition implementation is too expensive for the present 320-point search problem.
3. The earlier 5.9444x query reduction was only an oracle-query opportunity; once objective-evaluation cost is included, that advantage disappears for this implementation.
4. Routing this 24-qubit arithmetic circuit to Fez or compiling all six Grover rounds would add cost without answering the main bottleneck.

## Next experiment

Before any hardware routing, test whether the exact threshold predicate has a much smaller Boolean/structured implementation on the 9 parameter bits. This should be treated as an oracle-compression audit, not as proof of scalable quantum advantage: a truth-table-minimized predicate can exploit this fixed 320-point instance and does not replace a scalable coherent surrogate for larger parameter grids.

A useful comparison is therefore:

- table-state oracle: cheapest fixed-instance baseline;
- minimized Boolean predicate: fixed-instance structured lower-cost challenger;
- coherent arithmetic oracle: scalable-formula baseline.

Only if a scalable structured oracle remains cheap as the parameter grid grows would a larger quantum-search study be justified.

## Boundaries

- Zero QPU jobs.
- Fully connected synthetic backend only for this arithmetic probe.
- No Fez calibration, fidelity, timing, or execution claim.
- The TCT objective is a reduced-order FAIR-MAST-seeded control-policy proxy, not sustained-fusion validation.
- The classical reduced-order surrogate is inexpensive; no practical runtime advantage is claimed.
- The arithmetic constants and threshold are classically frozen.
- No fault-tolerant or error-corrected resource estimate is included.
