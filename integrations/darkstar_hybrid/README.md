# Dark Star + recycled-QPE integration

This directory contains the clean research integration between the earlier Dark Star periodic-prime-space experiments and the recycled-register QPE model.

The benchmark uses **self-generated semiprimes only**. Its purpose is to test a heterogeneous routing idea:

1. classical preprocessing / close-factor midpoint pruning,
2. remaining order-finding uncertainty,
3. routing between classical handling and a quantum phase-estimation stage,
4. comparison of wide and recycled-QPE resource models.

It is not presented as a general RSA break. The wheel/residue layer is conventional modular filtering; its clearest measured advantage in these experiments is Fermat-midpoint pruning for deliberately close factors. The lambda/order diagnostics are exploratory.

## Run

From this directory:

```bash
./run_hybrid.sh \
  --trials 20 \
  --shots 1024 \
  --close-bits 28 32 36 40 \
  --close-steps 250000 \
  --quantum-bits 5 6 7 8 \
  --outdir hybrid_results_large
```

The simulator compares ideal/noisy wide-QPE and recycled-QPE behavior and reports modeled register width. Modular-arithmetic ancillas are deliberately excluded equally from the phase-register width comparison; the recycled model does not claim that the full Shor work register disappears.

## IBM hardware

Use the repository-level hardware tools instead of embedding credentials here:

```bash
cd ../..
./hardware/setup_open_plan.sh
source ~/ibm-6c2q-venv/bin/activate
python hardware/save_open_plan_account.py
python hardware/preflight_open_plan.py
```

Then use `hardware/ibm_6c2q_hardware_test.py` for real-QPU dynamic-circuit experiments.
