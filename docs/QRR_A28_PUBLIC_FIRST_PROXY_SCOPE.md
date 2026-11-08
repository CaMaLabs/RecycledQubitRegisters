# A28 first integration checkpoint

The runnable stdlib script `hardware/qrr_a28_public_first_arithmetic_proxy.py` combines the A24 public-first wheel gate with the A27 reversible-binary/ideal-Fourier small addition kernel. It tests classically split cases (N=35 with bases 2,8) and wheel-unresolved cases (N=143,221 with base 2). This is an **integration plumbing / accounting experiment**, not the promised direct comparison with the original Dark Star Fourier/NTT spectral pruning.

Run `python3 hardware/qrr_a28_public_first_arithmetic_proxy.py`. It should print status `PASS_PROXY_INTEGRATION_NOT_FULL_FOURIER_PRUNING`. It runs no QPU jobs and has no dependencies beyond Python standard library.

A28 full acceptance requires: import and validate the actual original Fourier/NTT pruning implementation and its constraints on matched public-only cohorts; distinguish work avoided by public-first factorization from reductions in quantum arithmetic; compile functionally equivalent reversible modular exponentiation with and without QFT arithmetic on the same backend; include recycled register widths and reset/feedforward timing; compare Quaspy and classical recovery success probabilities; and report expected total cost per factor, including failed quantum attempts and classical overhead. Until these conditions hold, all speedup fields must remain unknown.
