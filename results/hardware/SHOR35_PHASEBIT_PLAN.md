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

Seven bits is the next recommended preflight because it improves both strict and permissive discrimination while adding only one additional affine modular-power round. For the affine encoding the seventh phase round uses another `U^4` work step, i.e. two additional controlled CNOTs (`CCX`) before backend routing/synthesis.

Eight bits is also worth a transpile-only comparison. It gives much stronger separation from the uniform permissive baseline, but adds another dynamic round and a wider conventional QFT. The QPU run should use whichever of 7 or 8 bits gives the best combination of manageable compiled depth/CZ and statistical discrimination.

Recommended zero-QPU-cost commands:

```bash
python hardware/ibm_shor35_affine_matched.py \
  --backend ibm_fez \
  --phase-bits 7 \
  --shots 512 \
  --optimization-level 3 \
  --transpile-only

python hardware/ibm_shor35_affine_matched.py \
  --backend ibm_fez \
  --phase-bits 8 \
  --shots 512 \
  --optimization-level 3 \
  --transpile-only
```

Do not spend QPU time until those two resource profiles are compared against the six-bit affine baseline (`recycled depth=466, CZ=137`; `wide depth=583, CZ=212`).
