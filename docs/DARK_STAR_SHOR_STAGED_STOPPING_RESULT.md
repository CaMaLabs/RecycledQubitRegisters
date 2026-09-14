# Dark Star / Shor staged stopping result

Date: 2026-09-14

The staged stopping-time audit moved the Dark-Star/Shor investigation beyond a validation-only precision bound.  It simulated a public adaptive/recycled workflow that increases phase precision only when strict continued-fraction candidates fail direct modular verification.  The true order is used only to generate ideal QPE samples and to score the simulation after the fact; it is not supplied to the public stop rule.

## N=209 public-cube probe

For `N=209`, seed base `a=3`, the public rule `L=3 when N mod 3 == 2` gives transformed base `27`.  The same public GCD/repeated-squaring guardrail does not factor the instance before quantum work.

Across 2000 conservative ideal staged sessions:

| Metric | baseline a=3 | public cube a=27 |
|---|---:|---:|
| validation order | 90 | 30 |
| success rate | 92.60% | 98.65% |
| mean stop precision | 12.64 bits | 9.73 bits |
| median stop precision | 12 bits | 10 bits |
| mean cumulative phase-round executions | 157.58 | 92.83 |

This corresponds to about `2.91` fewer phase bits at stopping and about a `41%` reduction in cumulative phase-round executions for this small example.

## Paired dataset result

The default 600-semiprime / 4800-row audit produced the following paired-success results relative to baseline:

| Policy | mean stop bits saved | fraction stopping lower | mean cumulative round ratio | mean cumulative round reduction |
|---|---:|---:|---:|---:|
| cube all, `L=3` | 2.14 | 61.76% | 0.8923 | 10.77% |
| PTP conditional cube | 1.29 | 52.04% | 0.9493 | 5.07% |
| `L=105` | 5.11 | 79.57% | 0.7378 | 26.22% |
| `L=1155` | 5.85 | 82.38% | 0.7038 | 29.62% |
| `L=15015` | 6.40 | 83.10% | 0.6823 | 31.77% |

The PTP-specific conditional rule therefore shows a modest but positive order-blind adaptive resource reduction in this conservative ideal simulation.  The larger smooth odd exponents produce substantially larger reductions but should be described as generic odd-power / p-1-like preconditioning, not as uniquely derived from the PTP paper.

## Important boundary

This is still an ideal algorithm-level Monte Carlo result, not a hardware speedup measurement.  The simulation credits only the nearest ideal QPE bin and treats every stage as a fresh rerun, which is conservative with respect to useful non-nearest outcomes and phase-work reuse.  However, cumulative phase rounds weight every QPE round equally; actual modular-power circuits can have different native costs.

Therefore the next gate is native-cost weighting rather than QPU submission.

## Next zero-QPU compiler gate

`hardware/ibm_shor209_public_cube_staged_cost_preflight.py` compiles the full 8-bit residue modular unitary for `N=209` at staged recycled precisions `4,6,...,16` for both base 3 and public transformed base 27.  Circuit construction uses only `N`, the public base, and `base^(2^k) mod N`; no order or factor is supplied.  The implementation uses the same exact direct-transposition full-register synthesis developed for the generic N=35 path.

The script then replays the conservative staged stopping sessions and weights every attempted shot by the best compiled native CZ count for that stage.

Run:

```bash
cd ~/Downloads/RecycledQubitRegisters
git pull --rebase
source ~/ibm-6c2q-venv/bin/activate

python hardware/ibm_shor209_public_cube_staged_cost_preflight.py \
  --backend ibm_fez \
  --profile 1_clean_kg24 \
  --optimization-level 3 \
  --seeds 2026,8776,9401
```

This contacts IBM only to obtain the backend target and compile against it.  It does not invoke Sampler and submits no QPU jobs.

The decisive output is:

```text
===== N209 PAIRED NATIVE-COST RESULT =====
```

A positive result requires the transformed policy to lower cumulative native CZ execution cost on paired successful sessions, not merely lower the validation order or abstract phase-round count.
