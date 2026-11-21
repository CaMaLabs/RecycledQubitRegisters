# Research audit: evidence and limits

The source-of-truth inventory is `evidence/audit/history.json` and
`history.sqlite3`. It includes immutable Git blob/commit hashes, source docstrings,
archive file hashes, normalized receipts and the existing reconciled ledger.
No private official source or binary is redistributed.

| History | Finding | Generalizable implementation / revisit criterion |
| --- | --- | --- |
| K006–K013, K062–K071, K091–K113 | Conservative cancellation, free phase folding, nonlinear/affine local rewrites; some exact/full PASS results had unchanged cost | Preserve K099; exact local plugins must distinguish free changes from scored ones |
| K015–K027 | Arithmetic scheduling, precision, mutagenic and hybrid searches ran; several campaigns stopped at finite candidate budgets or partial verification | Do not interpret incomplete searches as mathematical impossibility; record actual budget/config |
| K028–K047 | Larger arithmetic/recycling architectures had real local improvements but huge costs versus 62-qubit Helios; many prefix failures | Only revisit with an explicit complete qubit/executed-cost budget |
| K049–K056, K073–K086 | Walsh/Fourier, monomial, Horner, piecewise and range-reduced arithmetic were explored; many only numeric or prefix verified | No unimplemented method is credited as a functional engine plugin |
| K058, K062, K067, K092 | Full historical receipts exist, while short-prefix costs differ materially | Retain exact `verified_shots`, SHA and seed evidence; source gate savings do not imply score savings |
| K098 | Independent phase drops/perturbations failed or worsened full cost in the archived reconciliation | Revisit only as a joint compensated full-domain numerical construction |
| K114–K126 | Encoding, normalization, Chebyshev/Horner, cubic and ROM numerical/resource studies; incomplete integration | Preserve numeric/resource outcomes; do not claim complete circuit success |
| K127 | Symbolic predicate screen found no savings; BDD exceeded node budget | BDD exhaustion is inconclusive, not a proof of no equivalent predicates |
| K129–K131 | Restricted condition fusion and deterministic-prefix identity screening found no scored saving | These scopes do not establish a global no-go after measurement |
| K136–K138 | Local ANF/nonlinear-rank lower bounds were tight for many isolated motifs; other windows exceeded caps | Local optimality assumptions cannot be extended to whole measured circuits |
| K139–K143 | Measurement feedback/phase-congruence analysis; free gate rewrites without scored saving | Requires a complete phase/distribution proof before a scored channel rewrite |
| K149–K168 | Lookup/Newton/Q14 resource studies; K168 exact ROM reproduced here | Useful subcircuit; full normalization, updates, phase encoding and liveness integration missing |
| K169–K183 accessible sources | More bounded synthesis/caching, baseline, constant-condition and CSWAP studies exist | Sources are retained in inventory; unavailable result bodies remain unknown |
| K191, K195–K243 | Not present in any accessible repository branch/archive or environment | Explicitly unknown; requested baseline cannot be run here |

The earlier engine only expanded already-equivalent single mutations. Increasing
its nominal depth could not cross a temporarily inequivalent circuit expression.
The new MITM/SMT synthesizers solve a different bounded search problem and are
therefore a justified search extension. Neither can bypass proven independent-
wire lower bounds. The current stochastic walk only applies exact identities and
is accurately recorded as such.

The aggregate cost model matches the archived arithmetic identity Q*C exactly
where the relevant fields exist. It has **not** learned a trustworthy dynamic
execution/rotation-headroom predictor. The actual private official source and
new K191 verification must be inspected on the workstation before using such a
predictor to reject candidates.
