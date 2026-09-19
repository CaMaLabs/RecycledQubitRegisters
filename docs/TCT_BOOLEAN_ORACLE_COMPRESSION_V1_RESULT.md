# TCT Boolean Oracle Compression v1 Result

Date: 2026-09-18

## Scope

This records a zero-QPU fixed-instance Boolean-compression audit of the exact 8-state low-loss predicate derived from the FAIR-MAST-seeded TCT reduced-order search surface.

This is **not** a scalable surrogate implementation. It compresses the already-known truth table for this frozen 320-scenario problem and therefore must not be presented as end-to-end quantum advantage.

## Exact marked predicate

The 9-bit parameter register uses:

- standing bias: 2 bits
- boost reduction: 2 bits
- false-trigger-cost multiplier: 3 bits
- event-rate multiplier: 2 bits

The exact marked parameter-encoding states are:

`[14, 15, 30, 31, 46, 47, 63, 79]`

Decoded semantically, all eight marked states share:

- `boost_reduction = 0.70`
- `event_rate_multiplier = 0.25`

and then split by standing bias:

- `standing_bias = 0.25` with false-trigger-cost multiplier `0`, `0.5`, or `1.0`;
- `standing_bias = 0.35` with any of the five swept false-trigger-cost multipliers `0`, `0.5`, `1.0`, `2.0`, or `5.0`.

Thus the marked region is a compact structured corner of the parameter grid rather than eight unrelated points.

## Exact cube compression

The exhaustive Boolean-cube search found the same optimum under both objectives tested:

- minimum cube count: **4 cubes**
- minimum literal-square cost: **4 cubes**
- total literals: **32**
- literal-square sum: **256**

The four exact disjoint cubes are:

- `00001111-` covering states `[30, 31]`
- `000-01110` covering states `[14, 46]`
- `0001-1111` covering states `[47, 63]`
- `00-001111` covering states `[15, 79]`

Each cube has 8 fixed literals and one don't-care bit.

## Compiler comparison

Exact-width, fully connected, zero-QPU probe at optimization level 1:

### Direct eight-minterm table oracle

- logical width: 9 qubits
- CZ: **2,268**
- depth: **9,310**
- size: **14,021**
- weighted interaction edges: 24
- total two-qubit interaction weight: 2,268

### Four-cube compressed oracle

- logical width: 9 qubits
- CZ: **516**
- depth: **2,421**
- size: **3,518**
- weighted interaction edges: 34
- total two-qubit interaction weight: 516

Ratios relative to the direct table oracle:

- CZ ratio: **0.227513** → **77.25% fewer CZ**
- depth ratio: **0.260043** → **74.00% lower depth**
- size ratio: about **0.2509** → about **74.9% smaller compiled size**

The interaction graph becomes somewhat denser in edge count (34 vs 24), but total two-qubit weight drops sharply.

## Relationship to the reversible arithmetic oracle

The coherent arithmetic oracle for the same reduced-order objective required:

- 24 logical qubits
- 272,126 CZ
- depth 1,083,704

The four-cube fixed-instance oracle therefore uses roughly:

- **527x fewer CZ** than the arithmetic oracle;
- **448x lower depth** than the arithmetic oracle;
- 9 logical qubits instead of 24.

That comparison is methodologically asymmetric: the arithmetic oracle computes the objective coherently from the model, while the Boolean oracle exploits the already-known marked truth table. The large compression therefore does not rescue an end-to-end quantum-speedup claim for this 320-point problem.

## Interpretation

1. The exact low-loss TCT region has strong Boolean structure in the chosen parameter encoding.
2. A truth-table oracle can exploit that structure to cut compiler cost by roughly three quarters relative to direct eight-minterm marking.
3. The present coherent arithmetic implementation remains far too costly for the 320-scenario problem despite the idealized Grover query reduction.
4. The structured marked predicate suggests a useful next compiler experiment: factor the common semantic conditions once (`boost=0.70`, `event-rate multiplier=0.25`, high-bias branch) and compare a shared-control / ESOP implementation against the four independent cubes.

## Boundaries

- Zero QPU jobs.
- This is a fixed-instance Boolean synthesis result, not a scalable surrogate oracle.
- No end-to-end quantum speedup is claimed.
- The TCT objective remains a reduced-order FAIR-MAST-seeded control proxy, not sustained-fusion validation.
- The Nighthawk/Phoenix topology issue is not involved in this fully connected probe.
