# Further advance search: measurement-based arithmetic and a new classical claim

Research lead: Chase Lunsford / CaMaLabs. October 31, 2026.

**The previous numerical improvement is insufficient for a free RSA-2048
break. Neither additional lead examined here supplies one.** This audit adds
an implemented arithmetic construction and a concrete finite-size test of a
new classical factoring claim. External spend, QPU jobs, and hosted CI: zero.

## Measurement-based constant-workspace addition: implemented, but rejected for N35

Gidney's [constant-workspace adder](https://arxiv.org/abs/2507.23079) uses
measurement-based carry deletion and later phase correction. Its constructions
use three clean workspace qubits and approximately 4n Toffolis, or two clean
plus n-2 dirty workspace qubits and approximately 3n Toffolis. These are useful
asymptotic arithmetic results; their physical usefulness depends on compilation
and measurement costs.

The previous repo study cited this paper without implementing its construction.
This change adds an adapter to the author's actual generator at
[Strilanc/classical-quantum-adder](https://github.com/Strilanc/classical-quantum-adder),
commit `52618a2dac958af834519a4c88fb8c1ac0dfb9c6`. Upstream code is an external
dependency and is not vendored or represented as original CaMaLabs work.

The adapter handles a reference-export limitation: repeated quantum offset
controls can prevent the generator's QASM exporter from selecting distinct
parity pivots. Row reduction of the affine equations p=1 gives equivalent
conjunctions with distinct pivots. The emitted circuit includes classical phase
feedback and a physical reset after each destructive X measurement. Declared
reinitializations already satisfied by those resets emit no duplicate reset.

Correctness checks passed:

- 166 adder specifications, covering every constant at widths 1 through 6 for
  the three-clean variant; every constant at widths 1 through 4 for the dirty
  variant; and ten specified constants at width 6 with dirty workspace.
- 486,224 input/measurement-transcript paths, each checked on both the original
  and lowered operation streams. Every input target, control, and dirty value
  is covered within each specification. For a fixed transcript the resulting
  Kraus map is the ideal addition times a common scalar, preserving relative
  phase and arbitrary entanglement. Clean workspace returns to zero; dirty
  workspace is restored. These two streams use the same integer interpreter.
- A separate sparse statevector interpreter of the emitted Qiskit instructions
  checks coherent inputs spanning all target/control values for ten width-6
  constants and every measurement transcript. Maximum amplitude errors are
  below 1e-12. Removing the carry phase corrections is detected by the tests.
- The six actual N35 controlled powers cover all 768 phase-control/work inputs,
  including disabled and invalid residues. At 18,432 actual addition boundaries,
  the old circuit's carry workspace is clean. Replacing the additions by their
  proven ideal channels preserves the complete power operation by composition.
  This is not enumeration of all full-circuit measurement transcripts.

Both cached constant-adder references are replaced: the positive modular arm
holds a function reference separately from the signed arm. They are restored
after the experiment. This is broader substitution than changing only the
signed arm's module attribute.

The plan was frozen before scoring: bases 2 and 8, four recycled phase bits,
four compiler seeds, the same initial layout, Qiskit 2.6.1, optimization level 1,
and a synthetic bidirectional line of 23 qubits. No IBM backend was contacted.
The unchanged comparator still needs six carry wires, so using a three-clean
adder does **not** reduce the complete circuit below 23 active qubits.

| Base | Seed | Baseline CZ | MBU CZ | Baseline structural depth | MBU structural depth |
|---:|---:|---:|---:|---:|---:|
| 2 | 509 | 35,841 | 48,977 | 76,409 | 88,819 |
| 2 | 1223 | 34,927 | 49,167 | 76,422 | 88,737 |
| 2 | 4093 | 34,582 | 49,160 | 76,316 | 87,773 |
| 2 | 8776 | 32,587 | 49,194 | 72,842 | 87,674 |
| 8 | 509 | 20,714 | 25,832 | 42,843 | 46,574 |
| 8 | 1223 | 20,493 | 25,526 | 42,482 | 46,345 |
| 8 | 4093 | 20,294 | 25,502 | 42,137 | 45,820 |
| 8 | 8776 | 19,487 | 25,625 | 41,062 | 44,966 |

**Zero of eight pairs pass the required strict CZ-and-depth improvement.**
Routed CZ counts increase 24.6%-51.0%; structural depth increases 8.7%-20.4%.
Measurement counts increase from 4 to 388 for base 2 and from 4 to 196 for base 8.
All conditional-body CZ gates are charged, using the worst branch; a top-level
`count_ops()` would omit them. Structural depth recursively includes branch
bodies and a decision step. It is an instruction dependency metric, not a
physical timing estimate. No measurement/feedforward latency advantage is
assumed. This result rejects this substitution on this target, not the paper's
asymptotic construction or every possible architecture.

The generator was also evaluated at widths 6, 16, 64, 256, 1024 and 2048, for
three fixed constant patterns and both workspace variants. At width 2048 its
controlled three-clean form has 8,182 Toffoli-style operations and 2,046
measurement/reset pairs; its controlled dirty form has 6,138 such operations
and 2,046 measurement/reset pairs, borrowing 2,046 dirty qubits. The selected
uncontrolled specializations use three and two fewer Toffolis respectively.
These are generated standalone adder counts, **not simulated 2048-qubit
channels, complete modular arithmetic counts, physical qubits, or an RSA run**.

## New classical claim: the finite-size parameters rule out this written engine

The October 28 repository
[SubexponentialDeterministicFactoring](https://github.com/IsaacRudich/SubexponentialDeterministicFactoring)
by Isaac Rudich and Louis-Martin Rousseau claims a Lean proof of a single
deterministic factoring machine with time N^{o(1)}. Inspected commit:
`c91cc3f4947caca8977e81a5d14244f73b5ae2b1`. The authors describe its constants
as astronomically large; their stronger square-root-log-log rate is a
conjecture. A proved asymptotic bound alone would not establish a practical
improvement over heuristic number-field sieving at RSA sizes.

An exact integer port of the inspected source parameters gives a more concrete
test. `UniParams.lean` sets K0=48 and K[d+1]=9*K[d]^16, and increments the
recursive level only when K[level+1]^40 <= n, where n is the **input bit length**.
The first level therefore requires at least `(9*48^16)^40` input bits: a
1,115-digit number, approximately 10^1114.16 bits. At n=2048 the level is zero.

With the source's remaining width formulas, n=2048 gives s=3 and
Ltop=90,192,960,553,530. The dense table fill in `UniEngine.lean` has
`48 * 2^(48*Ltop)` entries, and its zero-level brute-force expression has
`2^(48^2*Ltop)` summands. Thus even the table loop has an exponent of
4,329,262,106,569,440; the brute-force exponent is 207,804,581,115,333,120.
The parameter gate records these exact integers and declines to launch the
engine. This is a statement about this source's explicit dense loops, not a
factoring lower bound or a refutation of its asymptotic theorem.

Independent Lean kernel verification remains **uncompleted**. A local install
of the specified Lean 4.35.0 toolchain was attempted. `lean --version` failed
with `error: failed to locate application`, and `lake exe cache get` failed
with `error: could not detect the configuration of the Lake installation`.
These environment failures neither verify nor disprove the claimed theorem.
The finite-parameter calculation requires only integer arithmetic and is
separately tested at the exact first-level transition.

## Other architecture results checked

- [Cain et al., March 2026](https://arxiv.org/abs/2603.28627) analyze Shor on
  reconfigurable atomic hardware, with an approximately 10,000-qubit lower-space
  design under their architectural assumptions. This does not supply a machine
  accessible to this project.
- [Pappalardo et al., October 28](https://eprint.iacr.org/2026/2665) estimate
  RSA-2048 using 22,593 cat qubits in 3.14 days under their noise and timing
  assumptions. This lead was already noted in the preceding audit. It remains
  a specialized hardware estimate, not a zero-cost executed factorization.

## Reproduction

From the repo root with Python 3.12, install `requirements-gidney-mbu-audit.txt`
in an isolated environment, then obtain the external source snapshots:

```bash
git clone https://github.com/Strilanc/classical-quantum-adder /tmp/qrr-gidney-adder
git -C /tmp/qrr-gidney-adder checkout 52618a2dac958af834519a4c88fb8c1ac0dfb9c6
git clone https://github.com/IsaacRudich/SubexponentialDeterministicFactoring /tmp/qrr-subexp-factoring
git -C /tmp/qrr-subexp-factoring checkout c91cc3f4947caca8977e81a5d14244f73b5ae2b1
QRR_GIDNEY_UPSTREAM=/tmp/qrr-gidney-adder python -m unittest discover -s hardware -p test_qrr_gidney_mbu_adder.py -v
python -m unittest discover -s hardware -p test_qrr_subexp_parameter_gate.py -v
python hardware/qrr_gidney_mbu_audit.py --upstream /tmp/qrr-gidney-adder --compile --out /tmp/qrr-mbu-rerun
python hardware/qrr_subexp_parameter_gate.py --upstream /tmp/qrr-subexp-factoring --output /tmp/qrr-subexp-parameters.json
```

Ten contract tests pass. Original raw arithmetic results are losslessly saved
as `results/gidney_mbu_20261031/audit.json.gz`; the directory also contains the
frozen plan, readable summary, exact classical-claim gate, and checksums. The
baseline research path remains the default. This change adds experimental
adapters and rejection evidence; no practical RSA or ML-KEM break is claimed.
