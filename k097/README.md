# K097: branch-aware reuse and public-input constraints

Research lead: Chase Lunsford / CaMaLabs. Public source is the credited Heliosli qcc-circuits-live portfolio v101pk0_mx4_ay3. This follows the transfer matrix in k096. No leaderboard gain was found.

## Methods and outcomes

- QRR register reuse: exact Boolean propagation models feed-forward and condition stacks. HMR outcomes remain independent unknowns; unread classical bits start at zero. Only proven-zero scratch states end lifetimes. Registered inputs occupy fixed physical locations, with optional temporary borrowing between proven-zero boundaries. Large nonlinear expressions become opaque, which can miss opportunities but cannot establish a false zero. XOR remains exact.
- The earlier conservative run (unread bits unknown) found 55 algebraic zero closures, 754 reset closes and 831 lifetime segments. Peak width remained 62, including at the first bottleneck. The unchanged verifier passed all 3,133,452 valid x inputs at two shots each, seed 12345; component cost 95,345.60068460317. This receipt belongs specifically to that earlier conservative run, not the final initial-zero refinement. Final analysis has its own lifetime receipt and produces byte-identical KMX (SHA256 00c504fd1204029f5c37891fb0a5c6098d4fd183e7a58616a5ee19b6f38cf427), so that full-domain validation also covers the emitted final circuit.
- LWE/Dark Star style constraint filtering: 65,536 simulated trajectories suggested 20 possibly-zero nonlinear predicates. Exact SSA queries, with the actual zero-initialized classical state and arbitrary measurement outcomes, found SAT counterexamples for all 20. No gate deletion was accepted. Restricted witness-input UNSAT is explicitly never used as a global proof.
- Retained diagonal products: an experimental adapter substitutes cached AND controls into CCZ operations and uses measurement-based cleanup. An earlier prefix run passed but added one qubit and increased cost: static nonlinear savings did not translate into fewer dynamically executed gates under mutually exclusive guards. This is a rejected prototype, not an accepted candidate; that earlier temporary raw prefix receipt was not retained.
- Existing-product lookup found no substitutions in the earlier scan. Checkpoint/recompute is a prototype for clearing and restoring exactly reconstructible idle wires. The earlier scan found 2,455 possible intervals, mostly paid AND recomputation; none crossed the examined first width bottleneck. It has no accepted scored candidate. Positive-budget experiments require explicit --max-added-ccx.

The self-test checks condition-stack identities, classical predicate copies and 200 random Boolean polynomial pairs over eight assignments each. The verifier used is the accessible Inzainos/quantum-circuit-compilation mirror with kickmix 1.0.0; this is local verification, not a Kaggle-scored submission. Public baseline SHA256: 034c7c2a54d51e13aff6e62ec4c14997d3968b6c11122146c57290b1a1b8c7e2.

```bash
python k097/branch_symbolic_lifetimes.py --source /path/invsqrt.kmx --out /tmp/lifetimes --borrow-inputs
python k097/find_constraint_candidates.py --help
python k097/counterexample_completion.py --help
```

Receipts distinguish full-domain validation, candidate filtering and counterexample search. No sampling-only observation is treated as a quantum equivalence proof.
