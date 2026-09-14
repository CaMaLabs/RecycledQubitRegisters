# N=35 affine phase-bit discrimination plan

The six-bit affine-encoded `N=35`, `a=2`, `r=12` hardware run substantially reduced circuit cost but remained at the strict uniform-noise floor. The next variable to tune is phase-register precision rather than the modulus or work-register encoding.

Using the exact finite-precision order-12 distribution and the same current post-processor, the phase-bit tradeoff is:

| Phase bits | Ideal permissive recovery | Ideal strict direct-order recovery | Uniform permissive baseline | Uniform strict baseline |
|---:|---:|---:|---:|---:|
| 5 | 72.6563% | 0.0000% | 71.8750% | 0.0000% |
| 6 | 81.9135% | 11.4756% | 42.1875% | 3.1250% |
| 7 | 84.5102% | 14.2885% | 24.2188% | 3.1250% |
| 8 | 84.9399% | 14.9758% | 12.8906% | 2.3438% |
| 9 | 84.8674% | 14.9646% | 6.4453% | 1.1719% |

Five bits should not be used for the strict-order benchmark: under the current continued-fraction/direct-order rule it has zero strict ideal recovery and almost no separation between ideal and uniform under the permissive metric.

## Measured transpile-only resource profiles

The 7-bit and 8-bit affine circuits were transpiled on `ibm_fez` at optimization level 3 using matched shared-work placement. Both exact affine-orbit self-tests passed.

| Phase bits | Architecture | Logical qubits | Depth | Size | CZ |
|---:|---|---:|---:|---:|---:|
| 6 | recycled | 5 | 466 | 603 | 137 |
| 6 | wide | 10 | 583 | 889 | 212 |
| 7 | recycled | 5 | 536 | 693 | 156 |
| 7 | wide | 11 | 667 | 1095 | 257 |
| 8 | recycled | 5 | 607 | 782 | 175 |
| 8 | wide | 12 | 788 | 1372 | 331 |

The 7-bit selected region reported local mean CZ error about `0.2487%`; the 8-bit region about `0.2561%`. Both used recycled-ancilla `measure_2` error `0.4395%` at preflight time.

Relative to 7 bits, moving to 8 bits adds only 19 CZ gates and 71 depth to the recycled circuit, while reducing the permissive uniform-output baseline from 24.22% to 12.89% and the strict uniform baseline from 3.125% to 2.344%. The ideal strict direct-order probability also increases slightly from 14.29% to 14.98%.

## Selected next QPU experiment

Use **8 phase bits**. It gives substantially better signal-vs-uniform discrimination for a modest recycled-resource increase. The recycled 8-bit circuit remains below the earlier successful `N=21` recycled circuit in CZ count (`175` versus `193`) and below it in compiled depth (`607` versus `707`).

Recommended matched hardware run:

```bash
python hardware/ibm_shor35_affine_matched.py \
  --backend ibm_fez \
  --phase-bits 8 \
  --shots 512 \
  --optimization-level 3 \
  --max-execution-time 120
```

After the run, evaluate both the permissive factor-recovery score and the strict direct-order metric against the automatically computed uniform baselines. Do not claim successful `N=35` order finding unless the strict metric and/or the measured distribution separates materially from uniform noise.

Implementation note: the current affine self-test printout labels its gate-budget block `six_round_controlled_gate_budget` even when transpiling 7 or 8 phase bits. That field is diagnostic text for the original six-bit budget; the constructed circuits do execute all requested phase rounds, as confirmed by the transpiled 7- and 8-round measurement/reset counts.