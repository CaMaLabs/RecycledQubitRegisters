# A11 phase-register bit-flip result — user-executed 2026-10-30

Command: `hardware/qrr_quaspy_a11_bitflip_ab.py --upstream /tmp/qrr-indie-quaspy --max-pairs 0` on Quaspy research branch. Reported `status=PASS`, 512 paired synthetic holdout readouts per condition, zero work-limit failures and zero QPU jobs.

|Profile|CF verified|Quaspy verified|Uplift pp|CF powers/verified|Quaspy powers/verified|CF flips|Quaspy flips|
|---|---:|---:|---:|---:|---:|---:|---:|
|clean|152|398|48.046875|38.0263|115.4095|0|0|
|lsb|152|398|48.046875|38.1118|117.0402|512|512|
|msb|146|398|49.21875|40.5616|119.6106|512|512|
|single_random|17|38|4.1015625|349.8824|2170.2368|512|512|
|ber_0p001|132|354|43.359375|43.9091|142.7684|71|68|
|ber_0p01|67|154|16.9921875|88.1045|470.4156|614|592|
|ber_0p05|2|7|0.9765625|2952|12242|3096|3009|

Important: BER is independently applied to frequency-register bits, not calibrated physical quantum noise. Phase-register lengths differ between full CF and shorter Quaspy arms. Both recovery probabilities collapse under high corruption. Identical aggregate LSB/MSB outcomes do not prove per-readout invariance. This benchmark is no evidence of RSA-2048 factorization or QPU performance. Raw JSON stays on user workstation.
