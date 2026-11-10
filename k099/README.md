# K099: DQI register pressure and control-aware cancellation

Research lead: Chase Lunsford / CaMaLabs. Applies QRR A110 style exact control/write commutation to the credited public Heliosli qcc-circuits-live portfolio v101pk0_mx4_ay3. Preserve the public dataset CREDITS.md and LICENSE.md. Baseline circuit SHA256: e9f54be304cbdcda7306729c335b1a2314a45d0ca818e05cf60e45ddee969bc4.

**No scored resource gain.** The pass removed 8,982,144 Clifford instructions: 8,981,916 CX, 196 SWAP and 32 X. Text lines fell from 58,341,262 to 49,359,118; headers and annotations are included in those totals. Width stayed 892 and static nonlinear count stayed 395,586. Reset-split lifetime analysis also retained width 892: all 840 registered syndrome wires and 52 work wires overlap at the peak.

The unchanged DQI verifier returned PASS for both baseline and candidate on the same 4,096-shot draw, seed 12345, batch 256, one worker, full m=4095, n=70, degree=12 problem. Both had zero value/phase errors, dynamic Toffoli count 395,303.9875488281 and cost 938,798,937,999.2799. This is a smoke test, **not the default 102,400-shot validation or a Kaggle submission**. One timing observation was 14.50 seconds baseline versus 12.42 seconds candidate; this is not a repeated performance benchmark.

The streaming cancellation engine buffers 2,048 instructions and uses conservative pairwise commutation. Unknown operations, conditions, classical updates, measurements and metadata are hard barriers. Nonlinear gates can be crossed only when the implemented exact commutation rules permit it; no nonlinear gate was removed here. Its self-test exhaustively checked 3,884 accepted gate-pair commutations on 16 basis states, including phase, and checked a conditional barrier.

```bash
g++ -O3 -std=c++17 k099/dqi_commuting_cancel.cpp -o /tmp/dqi_cancel
/tmp/dqi_cancel --self-test
/tmp/dqi_cancel /path/dqi.kmx /tmp/dqi-candidate.kmx /tmp/cancellation.json
python k099/verify_pair.py --baseline /path/dqi.kmb --candidate /path/dqi-candidate.kmb --verifiers /path/verifiers --out /tmp/check --shots 4096
```

Decode and compile KMX/KMB with kickmix 1.0.0 before/after the pass. Receipts record exact verifier commands, baseline and candidate outputs, instruction removal and register pressure. The verifier mirror is Inzainos/quantum-circuit-compilation, the same accessible mirror used in k098. Large third-party circuit binaries are not redistributed here.
