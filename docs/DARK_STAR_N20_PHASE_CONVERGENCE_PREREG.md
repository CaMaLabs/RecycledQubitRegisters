# Preregistered independent numerical convergence check of frozen n20 v3

Date: 2026-10-14 Pacific. Research lead Chase Lunsford / CaMaLabs.

This is **NOT another independently sampled semiprime population**. It tests the numerical stability of the already completed n20 v3 selected-N experiment, whose public survivor manifest is permanently frozen at SHA256
`a952fa4b57496136b29df7a3aca54a4361d4ec6ed5e0ee76c796602d5e840782`.

**Lock prior results before new numerical output:** preserve `docs/DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_RESULT.md` and its six raw result JSON files unchanged. Base run Actions 38677893149 used 4096 seeded phase samples for r>4096, exact enumeration otherwise.

## Locked independent convergence conditions

- SAME 72 selected 20-bit N/base, same six ell-strata/panels, same five public policy decisions.
- SAME ideal nearest-bin-only staged QPE, strict public factor-producing CF/GCD verdict, polynomial reversible modular arithmetic logical CCX, and same phase stages 4,6,...,40 with 4 shots/stage. No full-bin or hardware claims.
- **Independent fixed phase sampling salt** `QRR-n20-phase-v3-independent-validation-20261014-2049`.
- **8192** independent seeded uniform eigenphase numerator draws per (N,m) for r>8192; exhaustive r enumeration for r<=8192.
- Same CPython `random.Random(int.from_bytes(sha256(salt|N|m),'big'))` draw rule and common samples across policy candidates. The 95% Hoeffding per-stage absolute bound is `sqrt(log(40)/(2*8192))≈0.0150` where sampled; it is NOT a bound on the derived CCX-per-success ratio.
- Run all six panels independently and preserve complete row receipts. NO rerecruitment of N, no new hidden-order conditioning.
- Primary metric: ladder/always3 *successful-session* aggregate logical CCX ratio for ell3, ell5 and ell7 **trigger** strata, along with paired improvement/tie/worsening and both-success coverage; compare with original 4096-sample ratios 1.000000 / 0.994597 / 0.965400.
- Secondary: ladder/plain ratio 0.832899 / 0.799052 / 0.806628 in three trigger strata; reveal any changes of sign, coverage, paired counts or >0.03 absolute ratio drift (threshold preregistered before results), including controls.
- No fitted significance cutoff. If ladder/always3 gain changes sign, crosses parity, or is smaller than phase estimator uncertainty, report it as **numerically unresolved**. Exact sign stability across two seeds is supportive of a model trend, NOT rigorous confidence in a real QPU or new selector.
- A single-row bootstrap across N is not a substitute for changing the phase sampler; report both types of uncertainty separately.

Zero QPU, no IBM Runtime clients, credentials or paid plan use. Claim remains only approximate ideal nearest-bin sampled logical resource modeling on publicly classically selected toy semiprimes. No asymptotic Shor or RSA-scale conclusion.
