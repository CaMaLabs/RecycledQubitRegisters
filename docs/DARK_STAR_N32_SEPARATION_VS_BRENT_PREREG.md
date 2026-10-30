# Preregistered Dark Star N32 *factor-separation* study: PTP pruning versus optimized Brent

Research lead Chase Lunsford / CaMaLabs. Date 2026-10-29. **Zero QPU and zero paid/free IBM Runtime.** Follow-up to [N28 router versus identical Brent negative control](DARK_STAR_N28_ROUTER_VS_BRENT_SECONDARY_RESULT.md): the router lost 15/16 head-to-head, so optimized Brent is the primary benchmark from the start. Preserve N25–N28 records and don't pool them with this new original cohort. This is an algorithm-engineering benchmark on *small synthetic* semiprimes, not a factorization-complexity or quantum advantage claim.

## Freeze population BEFORE performance/secret factor evaluation

- Exactly **32-bit** composite N in `[2^31,2^32)`, built from distinct odd primes `21000 <= p < q <= 155000` such that gcd(N,210)=1.
- **Three deliberately constructed factor-separation strata (8 each, 24 total)** defined by the true Fermat midpoint displacement `D=(p+q)//2 - ceil(sqrt(p*q))`:
  - `near_0_8`: 0 ≤ D ≤ 8,
  - `middle_64_640`: 64 ≤ D ≤ 640,
  - `far_4096_16384`: 4096 ≤ D ≤ 16384.
- This stratum construction **uses synthetic primes ONLY to populate an experimental cohort**. Stratum and prime factors MUST NOT be passed to the factoring method, its public branch decision, source cost model, or time-benchmark code. The public algorithm accepts **only N**. Factor truth/stratum are used solely in the validation/reporting experiment; the audit must explicitly identify these data as **construction-generated**, not a feat of unknown-factor inference.
- SHA-sort all valid distinct N by `DARKSTAR-N32-SEPARATION-20261029|stratum|N` within each frozen stratum and take the first 8, no result-dependent dropping, no rerank. Freeze a PUBLIC manifest with N, stratum (experiment metadata ONLY), rank, population frame counts and a SHA of canonical rows, **no factors or measured costs**. Commit it to GitHub main via a distinct successful public freeze Actions workflow BEFORE running any factorization or reading validation-only p/q in scoring. Same selected N must not overlap prior N25–N28 by bit length.
- Precommit all algorithms, thresholds, seeds and success criterion in this document before freezing the public manifest. The benchmark algorithms use no stratum metadata. Exact factor truth may be reconstructed after **all public algorithms are timed** for a case; no factor-derived order/strategy selection.

## Fixed classical arms, fair resource accounting

Every algorithm gets only N, same fixed public residue semantics, no p/q, no hidden order, no performance oracle:

1. **B — optimized standalone Brent Pollard rho + complete wheel fallback:** test wheel primes 2,3,5,7; attempt the repository's same `brent_attempt` polynomial c=1,seed2 up to **1024 modular squarings**, then c=3,seed3 up to **512 modular squarings**; if both fail, complete wheel210 factor N. Log squarings, modular products, batched/fallback GCD, failures, elapsed, wheel fallback divisions. Total rho ceiling 1536.
2. **F — eight exact plain Fermat midpoint tests then B:** identical baseline B except a public eight-isqrt early check. This isolates cheap close-factor routing from PTP residue mathematics.
3. **Q — restored Dark Star safe quadratic-residue midpoint sieve then B:** QR modulus **M255255=3·5·7·11·13·17**, exact public necessary-square masks, at most **2048 midpoint positions** (`max_offset=2047`) and at most **96 expensive integer square roots**; after failure the EXACT same B budget and wheel fallback. This isolates PTP midpoint-pruning benefit including masks, modular checks and failed-Q cost.
4. **FQ — eight exact Fermat, then Q, then B:** costs all stages if needed; a near/middle adaptive classical portfolio but the *order is frozen*, NOT retrospectively selected by the hidden stratum. All QR bounds as Q.
5. **Wheel210 complete** and **original PTP LFK complete** independently as historical comparisons, not substitutes for the strong B baseline.
6. **Plain Fermat (2048 midpoint positions)** as a bounded comparator, allowed to return unresolved; don't count unresolved as successful nor quote time-to-success when it does not factor.
7. If desired as secondary, an N-only public selector `FQ if N%11 in {1,3,5} else F` can be measured as arbitrary exploratory ablation, but is **not** a validated predictor or part of primary protocol. Prefer no invented heuristic.

All four primary algorithm arms B,F,Q,FQ, wheel, LFK use the SAME complete factorization guarantee and verify factor p*q=N. Log every actual operations and every method-specific setup/elapsed; QR `found_at_offset`, positions, masked rejections, modular membership checks, root calls, prime masks, stop cap. **9 rotated/interleaved repetitions** per method, all raw time measurements preserved; calculate per-case median wall-time ratios in the same runner with randomized/rotated method invocation order predetermined by repeat index. Timings include any failed preliminary stages, factor validation, and wheel fallback, with NO synthetic-factor-generation time charged to the public algorithm. Label microsecond Python variability; don't translate CPU runtime into quantum CCX.

## Primary and secondary precommitted scientific gates

- PRIMARY **PTP-specific middle-stratum advantage** iff Q is faster than B in ≥6/8 `middle_64_640` cases **AND** faster than F in ≥6/8 same middle cases. Q involves public quadratic-residue pruning; F is the appropriate non-PTP early-Fermat competitor. No speedup claim if either gate fails.
- SECONDARY mixed-method portfolio FQ must be faster than B in ≥13/24 **across all three strata** to demonstrate a broad classical routing benefit. Record original pass/fail separately from per-stratum gains/losses.
- All factors must be exact for all 24 cases in B,F,Q,FQ,wheel,LFK. B, F, Q and FQ all share the **same fixed rho budget and same final wheel fallback**. No falsely claiming gain by omitting completion.
- Independently prove QR is a logically necessary filter and does not reject any true factor midpoint; verify every QR-found pair and that its integer x displacement agrees with the construction truth. Comparisons only after source and cohort are frozen.
- If QR gives fewer square-root tests but is slower end-to-end, preserve this negative. If PTP signals only appear in predetermined middle stratum, don't generalize to cryptographic semiprimes.
- Any router improvements proposed *after* this test require a **new population and preregistration**. ZERO actual quantum jobs, no QPU Runtime SDK.
