# Codex Handoff

## Objective
Beat the verified Helios inverse-square-root score 95,369.00696815242 with an officially verified lower-score Kickmix circuit while preserving the immutable reference.

## Repository State
Branch: experiment/a115-spin-qudit-arithmetic
HEAD: latest commit on branch; K127-K129 artifacts landed in 41e8e84c23052a427ebd6debb95b976afad06714; K130/K131 follow-up committed afterward
Last known good commit: K126 audit
Working tree status: clean after committing K126-K129 reports, scripts, and registry.

## Completed
- Fetched the requested branch in a separate worktree at /home/ubuntu/quantum-a26-mission; original dirty checkout remains untouched.
- Reconfirmed immutable baseline SHA-256 e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183.
- Ran existing K126 script from commit eb1df11 and saved its report under competition/k126/results/.
- K127 Boolean predicate screen found no identical normalized predicates among 48 Z_POW sites.
- K127 canonical BDD follow-up exceeded its explicit 10,000,000-node bound; this is inconclusive.
- K128 found no exact complementary phase-predicate pairs with a representable global constant.
- K129 found no eligible identical CCX/CCZ/CSWAP pair under distinct inline measurement-bit conditions among 7 events.
- K130 extended the search to 123 gates inside single-bit condition scopes and found no pair.
- K131 exhaustively screened all valid inputs through the first HMR; only R q22 was an identity, with zero scored-resource savings.
- Added experiment_registry.json with known Helios-relevant prior results.

## Current Work
Files: competition/k126/results/phase_ladder_audit.json; competition/k127/*; competition/k128/*; competition/k129/*; competition/k130/*; competition/k131/*; competition/experiment_registry.json.
K131 emitted only a no-score source candidate removing R q22; no scored candidate exists.

## Current Failure
K127 BDD equality screen exceeded 10,000,000 nodes during exact symbolic dataflow.
Likely cause: large intermediate Boolean functions and measurement-controlled dependencies.
Tried: input order q21..q0 then HMR outcomes; no unbounded run.

## Important Decisions
- K126 found 16 and 26 q28 phases separated by many gates; no adjacent merges.
- K098 already tested fixed-factor perturbations and dropping initial phase terms.
- K099-K113 covered broad cancellation, CSWAP decomposition, bounded reversible synthesis and Toffoli factoring.
- K098 archived score reports use a different source hash; they do not verify the current e7eb baseline.

## Verification
K126 read-only audit completed against the pinned baseline: 48 Z_POW sites, q28 ladders 16 and 26 sites, no adjacent q28 phases.
K127 DAG: 48 distinct normalized predicates; zero projected savings. K128: no complement pairs. K129/K130: no eligible condition-XOR pairs. K131: 3,133,452 inputs exhaustively simulated through line 151; one zero-cost R removal only.
No official verifier run for K127-K131 because no candidate has a scored-resource advantage.

## Next Actions
1. Review the registry and preserve historical artifacts.
2. Inspect later arithmetic/measurement regions for domain-restricted exact identities, not just the deterministic prefix.
3. Estimate saved executed Toffolis, rotations, or width before implementation.
4. Generate and officially verify only if a candidate has a plausible baseline win.

## Warnings
- Do not modify the original dirty checkout or overwrite historical results.
- Baseline is available in /home/ubuntu/quantum-a26-check/competition/k098/results/helios_immutable.kmx; it is not tracked in this worktree.
- Official verifier is in the existing runtime checkout at competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py.
