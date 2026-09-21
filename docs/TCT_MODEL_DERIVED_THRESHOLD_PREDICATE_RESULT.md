# TCT model-derived threshold predicate result

Date: 2026-09-20

## Scope

This records the zero-QPU derivation and compile of a compact TCT low-loss phase predicate directly from the reduced-order loss formula, fixed-point threshold, and frozen finite parameter codebooks.

Unlike the earlier semantic truth-table compression experiment, the oracle construction does **not** consume the frozen list of eight marked states. The marked list is read only after construction as a regression check.

The source reduced-order objective is

`L = A*event_mult*(1-bias)*(1-reachable*boost) + B*bias + C*false_mult`.

The fixed-point classification uses scale 10 and threshold 768.

## Model-derived feasibility pruning

The formula and threshold prove the following necessary code constraints by minimizing over all other parameters for each candidate code.

### Standing bias

- code 0, value 0.10: best possible score 915 -> cannot pass
- code 1, value 0.20: best possible score 814 -> cannot pass
- code 2, value 0.25: best possible score 763 -> can pass
- code 3, value 0.35: best possible score 661 -> can pass

Therefore only bias codes `{2,3}` can satisfy the threshold.

### Boost reduction

- code 0, value 0.25: best score 1010 -> cannot pass
- code 1, value 0.40: best score 894 -> cannot pass
- code 2, value 0.55: best score 778 -> cannot pass
- code 3, value 0.70: best score 661 -> can pass

Therefore boost code `3` is required.

### Event-rate multiplier

- code 0, value 0.25: best score 661 -> can pass
- code 1, value 0.50: best score 1322 -> cannot pass
- code 2, value 1.00: best score 2644 -> cannot pass
- code 3, value 2.00: best score 5286 -> cannot pass

Therefore event-rate code `0` is required.

### False-trigger multiplier

All five valid false-trigger codes can pass for at least one remaining parameter assignment, so the threshold does not imply one unconditional false-code restriction.

After applying the model-derived common constraints, the remaining conditional rule is:

- bias code 2 -> false codes `{0,1,2}`
- bias code 3 -> false codes `{0,1,2,3,4}`

## Derived Boolean predicate

The common parameter-bit constraints are:

`q1=1, q2=1, q3=1, q7=0, q8=0`

The remaining local bits are:

`[q0, q4, q5, q6]`

The minimum local ESOP contains three terms:

- `0---`
- `0110`
- `1001`

The resulting model-derived marked basis states are:

`[14, 15, 30, 31, 46, 47, 63, 79]`

The synthesized full 9-bit predicate was verified over all 512 parameter-register basis states. Only after that verification was it compared with the frozen marked-state list; the independent regression check matched exactly.

## Compiler result

### One Grover round

- logical width: 10 qubits, including one clean factoring ancilla
- CZ: 199
- depth: 1,013
- size: 1,365
- weighted interaction edges: 21

### Six Grover rounds

- logical width: 10 qubits
- CZ: **1,194**
- depth: **5,973**
- size: **8,055**
- weighted interaction edges: 21

## Comparison with the validated grid-factored arithmetic oracle

Six-round grid-factored coherent arithmetic:

- width: 25 qubits
- CZ: 42,756
- depth: 132,481

Six-round model-derived threshold predicate:

- width: 10 qubits
- CZ: 1,194
- depth: 5,973

Therefore the model-derived specialization gives:

- **97.21% fewer CZ gates**
- **95.49% lower compiled depth**
- **60% lower logical width**

The compiled circuit is numerically identical to the previously discovered semantic-factored ESOP circuit, but the methodological provenance is stronger: the predicate is derived from the reduced-order model inequality and codebooks rather than from a prelisted marked truth table.

## Interpretation

This closes the gap between the expensive coherent arithmetic evaluator and the cheap fixed-instance truth-table predicate for this frozen finite codebook. The threshold boundary itself collapses to a compact Boolean rule, so a 16-qubit score accumulator and reversible comparator are unnecessary for this specific model/grid combination.

This does **not** imply that arbitrary TCT objectives, different thresholds, different parameter grids, or continuous parameter spaces will admit the same compact predicate. The result remains a finite-codebook model specialization rather than a general-purpose reversible numerical evaluator.

The next hardware-relevant test is a fresh Fez patch/calibration sweep of this 10-qubit six-round model-derived circuit. Because the earlier 25-qubit arithmetic circuit was dominated by CZ exposure and coherence time, the key question is whether the roughly 100x smaller routed workload crosses into a regime where a limited raw-QPU experiment becomes technically meaningful.

## Boundaries

- Zero QPU jobs submitted.
- Reduced-order FAIR-MAST-seeded objective only.
- Frozen finite parameter codebooks and fixed threshold.
- Model-derived finite predicate, not general scalable arithmetic.
- No fusion-physics validation.
- No fault-tolerant resource estimate.
- No end-to-end quantum-speedup claim.
- The 320-point classical search remains trivial relative to current quantum execution overhead.
