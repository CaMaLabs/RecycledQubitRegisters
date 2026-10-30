# PRE-REGISTERED independent N34 Dark Star *anytime interleaved* PTP/Brent falsification

Research lead: Chase Lunsford / CaMaLabs. Date: 2026-10-29. **No real QPU, no IBM free/paid Runtime.** This is a new prospective experiment motivated by the documented FAILURE of the original N33 QR-density selector to avoid expensive far-factor QR work. N33 data are *prior hypothesis context*, never retested as a new independent cohort.

## Algorithm and exact budget, frozen before original sample selection

All algorithms accept only public `N` and a fixed method name. The `p,q`, true Fermat midpoint offset `D`, and synthetic construction stratum are never supplied. Guaranteed complete factorization of the synthetic N via final conventional wheel210 fallback, charged in timing.

**Resumable Brent state** is a true single continuing c1 stream (c=1, y0=2, max 1024 modular squarings, 16-product batch gcd), then if unfactored a separate c3 stream (c=3, y0=3, max512 modular squarings). Pauses **must not reset y,x,r,block product/collision state**, replay previous iterations, change a factor found, skip a pending gcd, or omit work costs. At every target checkpoint record exact cumulative `modular_squarings`, `modular_products`, `gcd_calls`; same resumable implementation and final budgets for B, F, Q, A. Include deterministic tests comparing uninterrupted and segmented state for **factor, operations and budget** on independent original small synthetic N. An intentional change to the old brent_attempt implementation is NOT allowed; the new stateful control implementation is used identically in all new arms. No hidden factor/order influences checkpoints.

Primary 4 complete factoring strategies:
- **B strong benchmark:** small base-prime tests 2/3/5/7; continuous resumable c1 Brent to1024, c3 to512 on failure, full wheel210 fallback.
- **F control:** as B, but first **eight exact Fermat square-root midpoint tests**.
- **Q full QR control:** as F, with fresh per-call public modular residue masks `M=255255=3·5·7·11·13·17` and **QR midpoint offsets 8..639 inclusive**, 64 maximal exact integer-root tests; then same B. Charge all fresh masks, every modular residue test, scanning, attempted isqrt, failed factor checks and cleanup.
- **A anytime proposed scheduler:** as F, but interleave a **single resumable** c1 Brent state with QR work as follows:
  1. c1 Brent to cumulative **96** squarings, stop on proper factor;
  2. QR scan offsets **8..71** inclusive (64 positions; same cumulative 64 exact sqrt upper bound), stop on factor;
  3. resume the SAME c1 Brent to **384** squarings, stop on factor;
  4. QR scan offsets **72..199**, stop on factor;
  5. resume c1 to **1024** squarings, stop on factor;
  6. QR scan offsets **200..639**, stop on factor;
  7. if still unresolved, c3 Brent to **512** squarings then complete wheel210 fallback.
  This is a **fixed resource schedule**, NOT a proximity predictor based on factor-separated group labels or sparse QR residues. Masks are created only when the first QR chunk is reached and retained for this invocation's later chunks; **not reused across trials/cases**. A properly paused rho state remains fully live across QR chunks. Bound total c1 and c3 squarings to1536 and QR root calls to64. When correct factors are found, immediately stop and charge only actually executed work.
- Historical independent reference complete wheel210 and complete PTP LFK also run; bounded Fermat640 (not complete) kept as diagnostic.
- Repeat each method **9** times on each N using deterministic rotated/interleaved method order. All original raw times, branch traces, full cost ledgers and original factor certificates preserved. Baseline methods must not get a cache subsidy for prime-specific N masks. Python performance is a noisy implementation benchmark, not asymptotic math. Do not compare unrelated CPU work units or quantum source CCX as interchangeable.

## Fresh, separately frozen population

Select **24 distinct 34-bit** synthetic semiprimes `2^33<=N<2^34` with odd prime pairs `55000<=p<q<=260000` coprime with210. Prospective strata based only on prime construction: 8 near `D=0..8`, 8 mid `D=64..640`, and 8 far `D=4096..16384`, with D=(p+q)//2-ceil(sqrt N). Sort each full synthetic candidate N stratum by SHA256 `DARKSTAR-N34-ANYTIME-20261029|stratum|N` then take first eight, without replacement and without method labels or results. The PUBLIC manifest stores only N, stratum **as cohort metadata not a method input**, rank, N bits/mod210, population counts, SHA256 of canonical rows, and fixed policy source Git blob. Do NOT put p,q,D or timing in the public manifest. Freeze this public manifest by a **separate successful GitHub Actions run/commit**, before running any factoring method on selected N; only then score and reveal factor truth for validation *after* all public-timed method invocations.

## Prospective pass/fail

All six complete methods B,F,Q,A,wheel210,PTP LFK must return exactly correct p*q=N and the paused/uninterrupted rho path must be independently proven equivalent. No failures silently dropped.

- **PRIMARY anytime merit gate:** A must be strictly faster than standalone B on **≥15/24** full original N *AND* strictly faster than full Q on **≥15/24** *AND* strictly faster than plain F on **≥13/24**, all paired per-input median wall time of nine interleaved repeats. Failure of any subtest = FAIL. All QR work, creation, pauses and failed prefix work charged.
- **SECONDARY middle-vs-far discipline:** middle A beats B ≥6/8, far A beats Q ≥6/8, and median far A/B slowdown ≤1.25 (casewise median). This deliberately tests whether early Brent checkpoints avoid repeating N33's disastrous far costs; fail if any element fails.
- If A happens to win by only near ordinary Fermat, explicitly label that. If a selector benefit comes solely from implementation bookkeeping differences, do NOT claim new mathematics. If PTP square-root pruning is correct but loses overall wall time, preserve both. All original receipts written before any further experiments and append results to `docs/RESEARCH_LOG.md`.
- Hardware, cryptographic-scale and quantum factorization claims prohibited absent real evidence. No paid/free IBM Runtime calls.
