# K147 — exact coherent AND-uncompute → measurement-release test

**Status: proposed exact local rewrite, NOT a Helios win.**
Literature: Gu et al., *Discovering state-of-the-art quantum circuits with large language models* (2026), https://arxiv.org/abs/2610.22367 ; https://github.com/andigu/uncompute ; Jeon/Huang/Cai, *Measurement-Based Uncomputation from an Error Correction Perspective*, https://arxiv.org/abs/2609.31605.

## Novelty against history
K139–K143 analyzed gadgets that **already use HMR** and classical phase feedback; they did not turn coherent leftover CCX uncomputation into measurement release. K103 canceled adjacent involutions, and K096/K138 screened unconditioned nonlinear windows; neither used a **fresh X-basis measurement and conditional CZ to remove an inverse CCX** with verified clean target.

## Precisely targeted candidate
If `t` is provably |0> from an earlier HMR reset; `a,b` remain stable; and an existing subroutine is:

```
CCX a b t      # t = a AND b, coherently
CX t o         # can occur multiple times with distinct targets
CCX a b t      # coherent uncompute, costs one scored Toffoli
```

then replace **only the final** CCX with:
```
HMR t m
CZ a b if m
```

For coherent superpositions, after measuring t in the X basis, outcome m contributes phase (-1)^(m*a*b). The conditioned CZ contributes the identical phase, so their product is +1. As t is reset to |0> by HMR, its final state equals that after the inverse CCX. This argument applies linearly to arbitrary entangled inputs. **It depends critically on t=0 initially, controls being unchanged, and the target having no other uses in the interval**.

The scan explicitly demands a prior HMR clean witness, rejects any intervening target mutation and control mutation, disallows unrecognized gates and measurements as barriers. It does **not** infer initial cleanliness from unproven register liveness.

## Reproduction
```bash
cd ~/quantum-a26-check
mkdir -p competition/k147
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/068b79f0091b6e0528ecbeaa845fe4df68c70de1/competition/k147/k147_measurement_release.py -o competition/k147/k147_measurement_release.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k147/k147_measurement_release.py --selftest
"$PY" competition/k147/k147_measurement_release.py --candidate competition/k147/results/one_release.kmx
```

Outputs `competition/k147/results/measurement_release.json`. A candidate source is created **only if a strict witness exists**; the immutable baseline remains unchanged. No candidate is auto-submitted or passed to the private official verifier. K147 verifies a symbolic phase identity, **not** the whole circuit's quantum channel or official scoring. If `hits=0`, log negative applicability without enlarging bounds blindly.

## Exact next verification if a hit exists
- Check generated KMX compiles to KMB with the existing kickmix package; inspect extra measurement bit and selected KMX line.
- Check width remains 62 and compare direct shot-execution Toffoli cost.
- Use existing `competition/k031/k031_full_domain_repair.py` verified API, with absolute KMB path, same prefix inputs/seed for rejection then all 3,133,452 shots and another seed. Require strict score <95,369.00696815242 and PASS.
- If not, close negative.

**Expected scored delta for one unconditional CCX saved at Q=62 is about -62, if added classical feed-forward is free and the precision model is unchanged.**

## Observed user VM outcome (2026-11-14)

```
K147_SELFTEST PASS coherent conditional phase proof and strict source witnesses
K147_RESULT {"hits": 0, "report": "competition/k147/results/measurement_release.json"}
```

**Disposition: NEGATIVE APPLICABILITY for the strict HMR-witnessed CCX/use/inverse-CCX pattern.** No source candidate generated and no official full-domain verifier run. This does not establish an impossibility theorem for measurement-based uncomputation or prove zero opportunities in other forms. Do not widen K147 bounds blindly or claim its synthetic proof as a Helios optimization.
