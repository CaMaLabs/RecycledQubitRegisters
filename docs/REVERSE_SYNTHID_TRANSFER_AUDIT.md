# Transfer review — Alosh Denny's reverse-SynthID vs CaMaLabs Dark Star quantum optimization

**Date:** 2026-10-15. **CaMaLabs research lead:** Chase Lunsford. **External author credited:** Alosh Denny, [aloshdenny/reverse-SynthID](https://github.com/aloshdenny/reverse-SynthID). **Cross-project review, not a claim of using or inventing his technique; no borrowed code, weights, data or watermark-bypass routines.**

## What the external project actually does

I inspected its README, `src/extraction/synthid_bypass_v4.py`, `scripts/build_codebook_v4.py`, `scripts/calibrate_from_feedback.py` and LICENSE. Reverse-SynthID analyzes **image watermark** residuals using Fourier spatial frequency, resolution/model-conditioned profiles, and **cross-color phase consensus**. A core heuristic is `C(k)=|mean_j exp(i φ_j(k))|`: genuine image-independent spectral carriers might remain phase-aligned across solid-color reference images, while image-content residuals decorrelate. It uses multiple background colors and resolutions; an independent validation-feedback loop recalibrates carrier weights. The repository README also documents a multi-stage image watermark suppression workflow, which is **irrelevant** to quantum factoring. Its stated detector/bypass success is author-reported; GitHub issues include reports that detection or bypass can fail or generate false positives on some models. Do not treat author metrics as independently established performance on modern datasets.

**License is NOT unrestricted open source.** The repository's `LICENSE` states research/non-commercial uses only, attribution and scholarly citation, distribution/derivative constraints, and separate written permission for commercial use. Even for CaMaLabs future commercialization, **do not copy source or trained codebooks without legal permission**. General mathematical ideas like phase circular statistics can be implemented independently; attribute intellectual inspiration to Alosh Denny, and avoid calling derived methodology his validated quantum invention.

## Transferable, narrowly

**(1) Cross-reference coherence as a *robustness diagnostic*, NOT a quantum oracle.** After we independently generate several matched seeded estimation traces, compute a descriptive circular concentration `|Σ exp(iφ)/K|` for a clearly specified complex *estimator-residual* representation. Genuine reproducibility must survive independent seeds and controlled perturbations; beware that QPE eigenphases themselves are uniformly mixed and no common phase orientation is guaranteed, so naively aligning complex FFT phase across Ns or eigenphases could manufacture structure. Never substitute a coherence peak for a factor-producing CF/GCD witness.

**(2) Matched-baseline and consensus across nuisance variables.** Use the same frozen N/base and random-number stream in a, a³ branches to reduce variance; compare across seed, phase precision and model variant. That control design is already present in CaMaLabs, and cross-condition stress testing can make it stronger without claiming an independent new theorem.

**(3) Noise separation with permutation/null controls.** To test proposed Fourier or spectral residual features, use matched noise and shuffled-phase controls, precommitted false-positive rate and blind heldout N. A high spectral amplitude alone is insufficient. Test whether adding a feature predicts the endpoint after controlling for known group (N mod3), order identity and classical prefilter; otherwise no actionable advantage.

**(4) Reproducible multi-resolution profiles** might suggest storing QPE stage precision, selected modular base, seed and noise variance as explicit indexed coordinates instead of averaging heterogeneous regimes. This applies to analysis quality, not a new factoring circuit.

## What does NOT transfer

- SynthID frequency carriers in 2D pixel space do **not** imply a universal frequency carrier for multiplicative order modulo an RSA-like composite. A spatial watermark can be intentionally correlated across images; QPE phases depend on eigenstate components and have no analogous fixed orientation across unrelated semiprimes.
- Spectral watermark subtraction, VAE regeneration, JPEG edits, and detector evasion have no mathematical rationale for improving quantum modular exponentiation or obtaining private factors. We will **not** integrate or test bypass routines in Dark Star.
- A high coherence score is not a successful factor, shortened resource cost, or reduction in logical qubits. These endpoints require separate proper public CF factor production, calibrated uncertainty, and clean-ancilla gate accounting.
- This review does not assert the reverse-SynthID repo's bypass rates are externally verified; open GitHub reports of model-dependent failure and false positives are reasons to use negative controls.

## Independence rule and suggested next pilot

The [fresh n22 precision holdout preregistration](DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_PREREG.md) was frozen **without applying any cross-repo features**. Do not add circular coherence to the currently frozen selector, sample frame or factor-production predicate. If this holdout produces clear enough evidence to justify another study, pre-register a wholly separate exploratory experiment comparing phase-summary stability on independent SHA-salted random seeds against shuffled-seed and matched-noise controls, with blind samples not present in current reports. Report false-positive rate and whether predictive utility survives controls, without importing source code.

**Conclusion:** methodological transfer **plausible at the level of multi-condition spectral-consensus diagnostics and controlled calibration only**. **No validated direct algorithmic transfer or quantum factoring speedup has been demonstrated.** Full credit to Alosh Denny for the reverse-SynthID investigation, and to Chase Lunsford/CaMaLabs for the separate QRR research direction.
