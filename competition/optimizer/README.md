# Autonomous KMX optimizer

This is a bounded research engine, **not a demonstrated Kaggle score win**.
The requested K191 circuit and private official verifier are absent from this
checkout. See `evidence/k191_attempt.json` for the actual failed K191 invocation.
The historical external K191 reference is **95368.85909206404**. The user's
Ubuntu campaign measured the baseline and composed candidate at the same
**95368.96201542337** with a full PASS.

The new entry point is `run_autonomous.py`. Existing `quantum_optimizer.py` and
`campaign.py` are preserved unchanged. They are legacy tools, not the new
verification/promotion pipeline.

## Run another circuit

The same scheduler accepts KMX, Qiskit QPY, and OpenQASM 2 or 3.

```bash
python -m pip install -r competition/optimizer/requirements-circuits.txt
python competition/optimizer/run_autonomous.py --source ./input.qasm --out ./circuit-run
```

KMX needs only the standard library for the quick profile. The K191 path keeps
its known SHA256 pin. Other inputs derive their own SHA256 automatically, and
`--expected-sha` can enforce a known SHA256. Use `--input-format` when the
filename extension does not identify the format. Use `--circuit-index N` to
select an entry in a QPY bundle. Run the same command with the same source and
output directory to resume.

QASM and QPY inputs produce `optimized.qpy` for the selected circuit. QPY
preserves the circuit's global phase, registers, metadata, and symbolic
parameters. The engine treats measurement, reset, classical control, custom
gates, continuous rotations and operations outside its supported gate set as
boundaries. It carries those instructions and their contents through in order.
A circuit made entirely of such instructions returns with the same operations.
OpenQASM parsing is limited to the features supported by the installed Qiskit
importer. For circuits generated in Cirq, PennyLane or another framework,
export to a supported OpenQASM format when the framework can represent their
operations there.

```python
from qiskit import qpy

with open("circuit-run/optimized.qpy", "rb") as stream:
    optimized, = qpy.load(stream)
```

The generic objective ranks local reductions by Toffoli-class count, then T
count, then instruction count. `summary.json` supplies input/output circuit
statistics and the output path. The invsqrt scoring contract applies to KMX.

Two passes are enabled in the default profiles:

- `identity_screen` adapts Dark Star's exact no-op elimination. It searches
  supported blocks for identity on every basis assignment, including arbitrary
  ancillary inputs and exact phase. This can discover a whole no-op block
  across different operations even if simple pair cancellation finds nothing.
- `parity_spectrum` adapts the use of spectral coordinates to expose
  constraints. It tracks affine Boolean parities through X, CX and SWAP, groups
  equal Walsh characters for T/S/Z-family phases, and combines their phases
  modulo eight. It preserves biased parity and rejects general angles.

Both passes require the independent exhaustive proof before making a change.
The historical K098 smoke run completed 20 bounded jobs with these methods
and found no improvements. The original scored K191 baseline was unavailable.

## Advanced methods

| Plugin | Coverage | Proven fixture reduction |
| --- | --- | --- |
| `conditional_phase` | Common read-only classical bit on contiguous diagonal KMX gates | Two conditional CCZ gates become one CCZ and two CX gates under the same bit. |
| `arithmetic` | Whole truth-table recognition of two-bit in-place add/subtract, small carry/add/subtract/multiply/comparator XOR oracles and generic quadratic output functions | Majority carry uses one CCX instead of three. A shared product can drive several output bits using one CCX. |
| `workspace_reuse` | Erases redundant compute/use/uncompute on a dirty helper with one or more targets. The original helper value still reaches every target. | Two CCX become one, including a fanout with an independent intervening gate. |
| `phase_function` | Exact Kickmix fixed-point angle merges and a four-dimensional Walsh null relation, with global phase included in proof | Two arbitrary rotations become one. A 15-T test phase block becomes identity. |
| `phase_predicate` | Exact bit-parallel predicates find equivalent phase sites through nonlinear reversible logic | Two rotations separated by arithmetic become one. |
| `affine_smt` | Incremental quadratic parity-product synthesis with a GF(2) rank lower bound and one Boolean variable per dictionary term. SQLite caches completed results by Boolean function and budget. | Four CCX terms become one CCX between affine basis changes. A rank-four pair proves the one-product bound UNSAT. |
| `mitm` | Bounded three-wire permutation synthesis with the shared SQLite function cache | Exact improvements in historical K098, with no change in directly scored gates. |
| Experimental | Small arithmetic layout inference can recognize several functions with the same truth table. Resource estimates are static and uncalibrated for candidate scoring. | Explicit source-level gates and exact local equivalence are reported. |
| Unsupported | General modular and scaled fixed-point arithmetic, clean-ancilla lifetime scheduling and global width reduction, approximate precision redistribution, Chebyshev/piecewise synthesis, calibrated noise-aware optimization, and domain-specific QPE equivalence. | These require additional semantics or resource models. |

The scheduler composes disjoint exact rewrites by replayable parent/child steps.
Queued official verification resumes after a budget interruption, and a solver
result or static estimate cannot promote a candidate. Inverse-square-root
verification requires the original installed official verifier and full input
coverage. For the historical lower-is-better invsqrt cost, choose a profile with this command.

```bash
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" -m pip install -r competition/optimizer/requirements-optional.txt
for profile in quick overnight extended; do
  "$PY" competition/optimizer/run_autonomous.py \
    --source "$HOME/quantum-a26-check/competition/k191/results/helios_k191.kmx" \
    --official-script "$HOME/quantum-a26-check/competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py" \
    --verify --score-direction minimize --reference-score 95368.85909206404 --profile "$profile" \
    --out "$HOME/quantum-optimizer-runs/k191-$profile" --resume
done
```

Run only the profile you need by editing the loop list. The measured baseline
governs official promotion. The summary reports `success` for a measured-baseline
improvement and `beats_reference` for the external comparison.

## What actually ran

- Inspected all accessible remote branches and the user's K001–K097 archive.
  Artifacts exist for **169/243 IDs**; **74 remain unknown**, including K191
  and K195–K243. Missing records are not failures or untried techniques.
- Normalized **277 archived PASS receipts**. Prefix/full shot counts are
  retained. These are historical evidence, not newly verified candidates.
- Reconstructed historical **K098** from the tracked K131 artifact by restoring
  `R q22` at original line 24. Its SHA256 exactly matches the historical pin:
  `e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183`.
- Completed **423 region experiments** on that historical circuit: **97 exact
  local rewrites**, **326 bounded no-improvement results**, **zero reductions
  in scored gates**, and **zero official verifications**. All 97 rewrites change
  free resources. They are not score improvements.
- Reproduced the preserved K168 ROM: **240 CCX, 388 CX, 48 X, 4 scratch**,
  25 standalone wires, 192 address/target checks with clean scratch. This
  subcircuit is not an integrated inverse-square-root solution.
- **32 tests passed**, including process isolation, two-worker candidate
  branching, interruption recovery, local proofs, and mock verifier promotion.
  Mock results test orchestration only; they are not Kaggle evidence.

`evidence/results.json`, the SQLite databases, `history.json`, and the campaign
registry contain the detailed records. `evidence/audit/cost_calibration.json`
checks Q*C against **219 archived receipts** containing all required fields:
maximum aggregate residual **0.0**. This does not calibrate execution frequency,
rotation precision or hypothetical transforms.

## Score direction and official defaults

**The historical invsqrt verifier's `score` is a cost to minimize.** Its recorded
formula is `Q * toffoli_equivalent`, with
`toffoli_equivalent = mean executed Toffoli-like + T-equivalent/4`.
Reaction depth is retained as an independent metric; no unsupported weight is
assigned to it. The Kaggle aggregate leaderboard score is a different quantity.
The request's `> 95368.859...` conflicts with those historical cost records.
Consequently verification requires explicit `--score-direction minimize` or
`maximize`. Both comparisons are supported; neither is silently inferred.

The private current scoring source could not be inspected here. The supplied
adapter checks the installed official CLI AST, loads its default problem
specification at n_p=10, pins its source hash, and preserves its **default domain,
shots, precision and error settings**. It does not copy historical one-shot
settings into a new full official verification. Every baseline is rechecked
with the same contract/seeds as its candidates. The adapter is tested with fake
assets but has not been executed against the unavailable private official module.
An API change fails closed; it does not weaken verification.

## Architecture and support

| Component | Implemented behavior |
| --- | --- |
| Plugins | `cancel`, `affine`, `factor`, `identity_screen`, `parity_spectrum`, `mitm`, `stochastic`, optional `smt` |
| Region selection | Scored-operation priority; width/span caps; barriers at unsupported instructions, classical changes, measurements and inline conditions |
| Scheduling | UCB over methods; progressively larger width/span/depth/state budgets; free-gate discoveries earn no reward |
| Persistence | SQLite WAL, source/seed/contract identity, canonical wire-renaming keys, bounded-failure deduplication, interrupted-job recovery |
| Candidate branches | Exact working branch and retained siblings; independent rewrites rediscovered on each new exact parent; official best stored separately |
| Local proof | Exhaustive arbitrary-dirty-input basis permutation and exact eighth-turn phase signature, up to 10 wires |
| Synthesis | Bidirectional permutation search <=3 wires; optional Z3 bit-parallel exact synthesis <=4 wires, <=16 slots |
| Verification | Pinned official subprocess, full expected shots, explicit structured PASS, finite metrics, two recorded seeds, strict objective improvement |
| Resources | Per-process address-space/CPU-affinity limits, solver/state/depth caps, wall deadline, bounded output files, process-group termination |
| Reproducibility | Seeds, configs, parent/child hashes, proof records, commands, receipts, implementation hashes and new-run source snapshots |

`methods.json` distinguishes functional, scoped, preserved-only and unimplemented
methods. There is **no** e-graph, genetic algorithm, simulated annealing, general
Pauli frame, arbitrary rotation quantizer, full arithmetic resynthesizer,
measurement-assisted ancilla recycler, or candidate-population beam search.
The stochastic plugin is a random exact-rewrite walk. The old beam engine is
retained but is not advertised as a functional new search backend.

All replacements are equivalent on arbitrary states of the supported wires,
including dirty ancillas and exact supported diagonal phases. This proves
coherent equivalence for that subset. The engine cannot cross an HMR/reset or
infer a clean ancilla from a comment. A transformation inside one unchanged
condition-stack scope is valid because the same unitary identity applies under
that guard; no transformation crosses the stack boundary.

The advanced phase passes parse unconditional KMX `Z_POW` instructions using
Kickmix's fixed-point angle convention. They merge equal affine or nonlinear
parity predicates and can apply an exact rank-four Walsh identity. Conditional
operations and measurements remain boundaries. Approximate passes require a
verified function/domain contract and are currently unsupported.
Static resource counts rank work. Official verification determines score.

MITM and SMT can traverse circuit implementations that do not individually
match the original at every intermediate rewrite. Unlike the legacy beam, they
can therefore find genuinely different bounded implementations. A timeout or
UNSAT for a limited alphabet/depth is never recorded as global optimality.
SMT returns its individual depth outcomes, including `unknown` reasons.

Concurrency applies to local search workers. Official checks run after a local
batch so solver/verifier pools do not overlap. The configured RAM value limits
each task's address space (divided across concurrent local workers), not a
cgroup-level aggregate resident-memory guarantee. The controller's region lists
have hard caps and registry export streams rows; retained data grows on disk.
Deadlines include queue generation, although a bounded in-progress queue
refresh can finish just after the deadline. Do not set concurrency above CPUs.

## Ubuntu: fetch without disturbing existing work

These commands create a separate checkout. They do not reset, clean or pull over
your experimental work. Choose another worktree path if it already exists.

```bash
cd "$HOME/quantum-a26-check"
git fetch https://github.com/CaMaLabs/RecycledQubitRegisters.git engine/autonomous-optimizer-20261120
git worktree add --detach "$HOME/qrr-autonomous-engine" FETCH_HEAD

PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" -m pip install -r "$HOME/qrr-autonomous-engine/competition/optimizer/requirements-optional.txt"
cd "$HOME/qrr-autonomous-engine"
"$PY" -m unittest discover -s competition/optimizer/tests -v
```

Run K191 using the assets in the original checkout:

```bash
"$PY" competition/optimizer/run_autonomous.py \
  --source "$HOME/quantum-a26-check/competition/k191/results/helios_k191.kmx" \
  --official-script "$HOME/quantum-a26-check/competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py" \
  --out "$HOME/quantum-optimizer-runs/k191" \
  --profile overnight --verify --score-direction minimize --resume
```

The default K191 SHA and reference value are pinned in the entry point. If the
actual numeric field is confirmed to be a larger-is-better score, select
`--score-direction maximize` explicitly in a **new** output directory. Changing
source, seed or verifier contract in an existing campaign is rejected.

Repeat the identical command to resume. Without `--verify` or `--contract`,
local experiments run and **official promotion is disabled**. `--hours` and
`--max-jobs` override a profile. `--config path.json` overrides individual fields:

```json
{
  "cpus": 4,
  "concurrency": 2,
  "memory_mb": 4096,
  "max_regions": 600,
  "max_jobs": 1000,
  "verifier_timeout": 2400,
  "methods": ["factor", "smt", "mitm", "stochastic"]
}
```

Profiles: `quick` (3 minutes, 60 jobs, standard library only), `overnight`
(8 hours, 10000 jobs), `extended` (48 hours, 100000 jobs). These are upper bounds,
not promises of enough distinct regions or useful discoveries. Install optional
Z3 for the long profiles; missing Z3 is recorded as unavailable, not a solver
success. The official verifier retains its own dependency requirements.

For a changed official interface, first inspect its current source/help. Supply
an explicit JSON `--contract` with script/hash, argv tokens, expected full shots,
metric field mapping, seeds and score direction. This escape hatch is for a
verified API change, not reduced-domain screening. Contract argv is never passed
to a shell. Every raw verifier metric is retained, including error, Toffoli,
rotation cost/precision, qubits and reaction depth.

## Results and replay

A campaign stores `experiments.sqlite3`, `registry.json`, `summary.json`,
content-addressed KMX files, per-task proof output, and verifier receipts/logs.
Only `OFFICIAL_PROMOTION` and `summary.best_official` establish a new verified
entry, after baseline verification and strict improvement. `LOCAL_IMPROVEMENT`
means only an exact local change with a lower static proxy.

Generated historical intermediate KMX files are omitted from Git to avoid
storing many 750 KB copies. Every replacement and parent hash is retained in
SQLite; replay checks all local proofs and final byte hashes:

```bash
python competition/optimizer/recover_historical_fixture.py --output /tmp/historical_k098.kmx
python competition/optimizer/replay_candidate.py \
  --database competition/optimizer/evidence/historical_k098/experiments.sqlite3 \
  --source /tmp/historical_k098.kmx \
  --candidate 2b16be0a48b4548cef8c9c181b0fa398d633ff6d824c532a496e0271a39c1c86 \
  --output /tmp/historical_exact_candidate.kmx
```

The recovery tool needs the pinned historical Git object. A full repository fetch
includes that existing branch; a single-branch shallow clone may need to fetch
`experiment/a115-spin-qudit-arithmetic` first. Recovery refuses to overwrite any
file and verifies the historical SHA. It is **not K191**.

Development runs found and fixed pending-parent reuse, disabled-method scheduling
and free-rewrite reward bugs. Those attempted jobs remain in the database.
Earlier development runs do not all have complete implementation snapshots; a
later SMT run does. New campaigns retain a source snapshot for every run.

## Strongest next work

1. Recheck K191 using the current official defaults and matched seeds before
   comparing any fresh value to the historical one-shot reference.
2. Recover K195–K243 results and the actual K191 modifications. Do not assume
   any of those methods were never tried.
3. Gate further independent-wire small-window synthesis by a specific lower-bound
   gap. K136–K138 already found many tight isolated motifs. The new solver removes
   a search limitation, not those lower bounds.
4. Prioritize post-HMR reachable-predicate/channel rewrites only after a complete
   measurement/phase proof is available. The present engine intentionally does
   not pretend to support that proof model.
5. Joint compensated phase/error-budget optimization remains more promising than
   another free Clifford cleanup, but needs a full-domain numerical certificate
   and a concrete reduction in executed rotations/T-equivalent cost. K098's
   independent angle perturbations are not such a certificate.

## Resume a saved K191 candidate

```bash
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/optimizer/run_autonomous.py \
  --source "$HOME/quantum-a26-check/competition/k191/results/helios_k191.kmx" \
  --out "$HOME/quantum-optimizer-runs/k191-validation" \
  --resume --profile overnight --verify-every 20 \
  --start-from 253ec4e00cab34e62fe457a055436ab09b755a724255a22af151fc8dc9ea870e
```

Explicit resume reuses the verifier contract and reference from the saved
database when omitted. The `--start-from` option replays the archived proof
chain against the pinned source and checks the candidate hash before switching
the search pointer. Previously checked candidates keep their receipts. The
controller queues verification after every 20 accumulated edits and at exit,
including when all edits are neutral under the static score proxy. To disable
the periodic and final checkpoints, pass `--verify-every 0`.

The conditional phase pass checks exact phase on the active branch and
preserves identity on the inactive branch. A different guard, classical write,
measurement, or condition-stack boundary splits the region. In a 90-job
historical K098 run, this pass found no reductions.
