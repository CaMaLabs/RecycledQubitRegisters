# Literature experiments — October 30, 2026

Research lead: Chase Lunsford / CaMaLabs. These are runnable, bounded CPU
experiments, with original result receipts in `results/literature_20261030/`.
No IBM account is opened, no QPU job is submitted, and no paid runtime is used.

## Implemented scope and results

| Direction | Implemented | Original local result | Remaining scope |
|---|---|---|---|
| Van Kirk/Gidney, arXiv:2610.06733 | Sparse complex-state traveling-eigenstate reference, backward Fibonacci accumulator updates, controlled multiplication probes, adaptive transcript tree, singleton-mask negative control, finite-grid phase diagnostic | Complete transcript distributions agree with direct Fibonacci powers at N15/N21/N35, including two generators for N35; singleton masks disagree | Gate-efficient mask preparation, optimized arithmetic, scalable adaptive-cell posterior, and complete Regev lattice postprocessing are not implemented by this reference |
| Nie et al., arXiv:2610.34446 | Lemma 3 seven-stage exact adder with the allowed direct small-width ladder; Eqs. 14–17 borrowed-register Pascal echo; constant-register reuse in existing N35 arithmetic | 5,460 adder and 512 dirty-echo basis cases pass; six controlled powers each pass 128 exact complex-phase/cleanup cases | The optimized logarithmic-depth forest synthesis and its asymptotic resource theorem are not reproduced |
| Complete circuit cost | Original selected source versus ladder constant additions; bases2/8, precision4/6/8, four seeds, same fixed layout and synthetic line target | **0/24 paired wins** in both CZ and depth; reject this candidate on this target | This target is not IBM Fez, calibration data, or physical hardware evidence |
| Dark Star stopping rule | Executable public-evidence gate defaults to existing strong Brent, optional fixed Fermat8 precheck; divisor-exclusion certificate actually charges every trial | Same-signature near/far examples both select Brent; tiny actual factor checks pass | Historical workflows remain available; external schedulers are not automatically redirected |

The new code preserves the existing selected arithmetic and historical receipts.
It does not install a losing candidate into the default research source.
The exact-phase checks establish coherent correctness by linearity for the
promised clean-helper subspace; they are not device noise/fidelity tests.

## Run

From the repository root, Python 3.12:

```bash
python3 -m venv .venv-literature
. .venv-literature/bin/activate
python -m pip install -r requirements-literature-20261030.txt
python hardware/qrr_masked_fibonacci_reference.py
python hardware/qrr_ladder_adder_literature_ab.py --compile --bits 4,6,8
python -m integrations.darkstar_hybrid.literature_continuation_gate --self-test
```

For a public integer using the new conservative entry point:

```bash
python -m integrations.darkstar_hybrid.literature_continuation_gate --N 713
```

The workflow `qrr-literature-20261030.yml` reruns CPU checks and uploads receipts
as artifacts. It has read-only repository permissions and does not commit or
overwrite archived scientific results. CI success means code completed; it
does not mean a candidate passed its scientific performance gate.

## Source provenance and transfer boundaries

- https://arxiv.org/abs/2610.06733 — Sections 2–3 supply the masked traveling-state construction. Exact public unit enumeration is charged and explicitly exponential. The finite-grid diagnostic does not use the paper's scalable posterior. Binary and Fibonacci schedules have equal probe counts but unequal unitary-power sums.
- https://arxiv.org/abs/2610.34446 — Lemma 3 and Eqs. 14–17. Downloaded PDF SHA256 `bea98263e0a08131c743e4066d1bd169fbdc644f8fa062f33ddd0ce85fc74a04`. The small-width ladder and naive echo do not justify claiming the optimal theorem's gate/depth bounds.
- Parent default-branch snapshot at inspection: `039b4ab5bedaeda8eaa3d446cfb09419190095ae`.

Next research should target the missing optimized constructions or a genuinely
different arithmetic network, with source proofs before complete-circuit cost.
A PTP midpoint sweep needs separate public structural evidence; modular
residue sparsity alone is not such evidence.
