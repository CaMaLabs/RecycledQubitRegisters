# K158 — shared normalization source audit

**Status:** read-only source-inspection experiment, not a normalization rewrite or gate saving.

K117–K123 already investigated exponent/mantissa range reduction and arithmetic approximations; K149–K153 used x=2^(2k)m. This experiment is different: audit the **existing pinned Helios KMX source** for actual input-dependent repeated arithmetic and potential retained normalization values without inventing exponent/mantissa register semantics from opcode proximity.

The script pins SHA256 e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183. It searches windows with 4+ input-register touches and 2+ nonlinear gates, ranks them, records input-register write frequencies, and extracts source excerpts. **This is only evidence gathering**: a frequent reference to input bits cannot establish duplicated normalization or a valid compute/use/uncompute replacement. K135–K138 studied motifs, so no repeats are declared reusable solely by shape.

~~~bash
cd ~/quantum-a26-check
mkdir -p competition/k158
curl -fL https://raw.githubusercontent.com/CaMaLabs/RecycledQubitRegisters/67a87536089633fa34ad8cae7a9c6d87b7ac2138/competition/k158/k158_normalization_reuse_audit.py -o competition/k158/k158_normalization_reuse_audit.py
PY="$HOME/.venvs/kaggle-k001/bin/python"
"$PY" competition/k158/k158_normalization_reuse_audit.py
~~~

Share competition/k158/results/normalization_audit.json (or the printed top regions). The next step is manual source provenance to identify if any particular exponent/mantissa representation is computed twice, its exact live range, and whether keeping it saves **executed** CCX with <=62 qubits. If none is identified, log this branch as unsupported rather than generate a speculative rewrite.

**No KMX candidate, score change, or verification claimed.**

## Independent user Ubuntu run (2026-11-16)

User reports \`K158_SUMMARY {"windows":201,"reported":24,"source_lines":53841,"status":"READ_ONLY_SOURCE_LOCALITY_NOT_NORMALIZATION_PROOF"}\`. Highest input-touch windows: 513–640 (180 touches, 113 writes, 5 CCX); 641–768 (180,122,3); 33281–33408 (168,121,3); 33793–33920 (165,120,3); 897–1024 (164,123,2); 33409–33536 (163,125,3); 34305–34432 (163,125,3); 33537–33664 (162,125,3). No source excerpts pasted yet; these counts do NOT prove duplicated normalization. Await \`normalization_audit.json\` before making register-provenance assertions.
