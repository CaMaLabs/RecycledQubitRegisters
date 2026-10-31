# A23 exact N35 recycled-phase -> Quaspy bridge — user-run 2026-10-30

`hardware/qrr_a23_exact_recycled_distribution_postprocess.py --upstream /tmp/qrr-indie-quaspy` returned `PASS_EXACT_IDEAL_BRIDGE`, zero QPU jobs. Full probability vector of the existing **ideal coherent-work branch model**, checked independently against exact finite QPE spectral mixture, then supplied to the public-only CF/Quaspy recovery routine for each outcome. No sampled hardware shots or full gate-level noisy dynamic circuit execution.

|Base|bits|Maximum ideal probability difference|CF weighted verified factor probability|Quaspy weighted probability|CF weighted modular power calls|Quaspy weighted modular power calls|
|---:|---:|---:|---:|---:|---:|---:|
|2|4|1.249000902703301e-16|0.0|N/A|1.09375|N/A|
|2|6|3.5388358909926865e-16|0.11475625909649509|N/A|1.0465252382698889|N/A|
|2|8|1.304512053934559e-15|0.292343312671948|0.9999999999999992|1.2347410232802996|10.999999999999996|
|8|4|7.570288943589365e-31|0.5|N/A|1.25|N/A|
|8|6|3.8976894982870434e-30|0.5|N/A|1.25|N/A|
|8|8|5.810372383060851e-29|0.5|1.0|1.25|8.0|

Quaspy requires N.bit_length() < phase bits <= 2*N.bit_length(), so 4/6 bit values are *ineligible* (not failed factors). No work limit failures. Quaspy uses significantly more public classical modular exponentiations. Strong **ideal** integration of exact recycled QPE branch probabilities and independent Quaspy factor verification on N35 only. Does not integrate Dark Star preconditioning or original periodic prime-table pruning and does not establish noisy hardware success or scalable factoring. A18 Fez native cost remains NO_GO. Preserve selected arithmetic and validated baseline.
