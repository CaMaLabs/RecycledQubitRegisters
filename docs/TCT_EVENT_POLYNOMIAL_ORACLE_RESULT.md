# TCT event polynomial oracle — compiler result

Date: 2026-09-19

## Scope

This records the zero-QPU compiler result for replacing the v1 reversible TCT oracle's 64 equality-pattern event-value selects with the exact multilinear/Mobius representation of the same frozen six-bit integer event function.

This remains finite-function synthesis over the frozen event/bias/boost grid. It is more structured than the 64-pattern lookup, but it is not yet a general reversible multiplier and is not evidence of end-to-end quantum advantage or fusion-physics validity.

## Exact synthesis

- logical width: 24 qubits
- event truth-table values: 64
- nonzero multilinear monomials: 54
- polynomial verification: exact over all 64 event/bias/boost assignments
- maximum polynomial degree: 6
- maximum absolute coefficient: 4,194

Degree distribution:

- degree 0: 1
- degree 1: 6
- degree 2: 13
- degree 3: 15
- degree 4: 12
- degree 5: 6
- degree 6: 1

The high-degree tail is largely a consequence of representing the already-rounded 64-value integer table exactly; it does not imply that the underlying physical loss formula is intrinsically degree six.

## Compiler comparison

| Circuit | CZ | Depth | Size | Weighted edges |
| --- | ---: | ---: | ---: | ---: |
| old 64-pattern event forward | 134,560 | 535,394 | 826,229 | 210 |
| exact polynomial event forward | 23,664 | 100,930 | 145,945 | 210 |
| full one-round polynomial oracle | 49,958 | 213,221 | 308,106 | 258 |

Event-block ratios relative to the old lookup:

- CZ ratio: `0.175862` -> **82.41% fewer CZ**
- depth ratio: `0.188515` -> **81.15% lower depth**

Full-oracle ratios relative to the original arithmetic v1 result (`272,126 CZ / 1,083,704 depth`):

- CZ ratio: `0.183584` -> **81.64% fewer CZ**
- depth ratio: `0.196752` -> **80.32% lower depth**

Thus exact Boolean-polynomial synthesis reduces the coherent arithmetic oracle by roughly a factor of 5.45 in CZ and 5.08 in depth without changing the 64 rounded event values.

## Interpretation

The result confirms that most of the previous arithmetic cost came from equality-pattern selection rather than from QFT shells, comparison, validity marking, or the diffuser. Replacing six-bit equality selects by the unique multilinear form is a major improvement.

However, 54 nonzero monomials remain, including many degree-3 through degree-6 controls. This is still much more expensive than the validated fixed-instance semantic oracle and still does not make the 320-point search competitive as an end-to-end quantum computation.

The next step should therefore stop preserving the *rounded 64-value table* as the implementation target. Instead, exploit the exact algebraic structure of the source model and parameter grids:

`L = A * event_mult * (1-bias) * (1-r*boost) + B*bias + C*false_mult`

For the frozen grids, bias and boost are affine in their two-bit codes, event multiplier is a power-of-two shift (`0.25, 0.5, 1, 2`), and the reviewed Mirnov+toroidal reachable fraction is rational (`38/59`). A classification-exact transformed integer score can therefore be synthesized with a low-degree bias/boost polynomial plus reversible controlled shifts, avoiding the artificial degree-six structure introduced by exact reproduction of independently rounded table entries.

## Boundaries

- Zero QPU jobs.
- Exact only for the frozen six-bit event table in this experiment.
- No scalable coherent-surrogate claim yet.
- No end-to-end quantum-speedup claim.
- No fusion-physics validation.
