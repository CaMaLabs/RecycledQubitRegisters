# N=35 affine cross-backend validation: IBM Marrakesh

This experiment repeats the frozen eight-bit affine `N=35`, `a=2`, `r=12` matched benchmark on a second IBM superconducting backend, `ibm_marrakesh`, without changing the mathematical circuit or adding backend-specific placement optimization before the run.

The purpose is to test whether the Fez result transfers to another superconducting QPU. The result is deliberately recorded as a mixed/negative cross-backend outcome rather than promoted as a successful strict replication.

## Preflight

The affine encoding self-test passed. `ibm_marrakesh` exposed dynamic `measure_2` support. The matched initial work-register placement was shared between architectures.

### Compiled resources

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Depth | 820 | **607** |
| Circuit size | 1347 | **782** |
| CZ gates | 329 | **175** |

The recycled circuit therefore compiled with exactly the same 5-qubit / depth-607 / 175-CZ resource counts as the original frozen Fez baseline. This makes the hardware comparison useful as a backend-independence test rather than a new circuit variant.

## Hardware result

Matched same-job run, 512 shots per architecture.

| Metric | Wide | Recycled | Uniform reference |
|---|---:|---:|---:|
| Permissive factor recovery | 16.0156% | **25.0000%** | 12.8906% |
| Strict direct-order recovery | 2.5391% (13/512) | **1.1719% (6/512)** | 2.34375% (12/512 expectation) |
| Hellinger fidelity to ideal | 0.2230 | **0.2998** | 0.2349 |
| TV distance to ideal | 0.8276 | **0.7304** | 0.8257 |

The recycled-minus-wide permissive factor-recovery gap was approximately **+8.98 percentage points**, about **3.58 standard errors** under the same simple independent-binomial comparison used elsewhere in this repository.

## Interpretation

This is **not a strict cross-backend replication** of the Fez order-12 result.

The recycled Marrakesh output retains a weaker distribution-level advantage: permissive factor recovery is well above the uniform-output baseline, Hellinger fidelity to the exact order-12 distribution is higher than the uniform reference, and TV distance is lower. The wide circuit remains close to the uniform reference.

However, the conservative strict direct-order metric does not survive. Recycled produces only 6/512 strict successes, below the 12/512 uniform expectation, while wide produces 13/512, essentially at the random floor. Therefore the experiment does not establish backend-portable strict recovery of `r=12`.

The result narrows the current claim:

- Fez: strict `r=12` signal reproduced across two unmodified runs and preserved under an independently selected optimized layout.
- Marrakesh, unoptimized baseline: broader order-correlated/permissive signal remains, but strict direct-order recovery fails.

This backend sensitivity is scientifically important. It is consistent with earlier QPE experiments in this project showing that dynamic-circuit performance can depend strongly on backend-specific calibration, mid-circuit measurement behavior, routing, and physical placement.

## Next experiment

Freeze this unoptimized Marrakesh result before making any backend-specific changes. Then run the zero-QPU calibration-aware layout optimizer on `ibm_marrakesh`. If the optimized transpilation is materially better, run a separate optimized Marrakesh matched job. That follow-up should be described as a hardware-aware rescue/optimization experiment, not as the clean cross-backend replication.

The broad and strict outcomes must continue to be reported separately.
