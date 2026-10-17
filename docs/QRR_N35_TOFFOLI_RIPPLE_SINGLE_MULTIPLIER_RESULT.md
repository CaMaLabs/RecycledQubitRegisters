# VERIFIED — N35 explicit ripple/Toffoli controlled modular multiplier: all 128 gate-basis cases correct, native CZ 27,929/29,822; QPU gate FAILS

**Research lead and originating research program:** Chase Lunsford / CaMaLabs. **Date:** October 16, 2026 Pacific (GitHub UTC October 17). **ZERO QPU submitted; zero Open Plan runtime used; no hardware measurements in this experiment.**

## Why this is a useful but LIMITED experimental milestone

The user's [first actual IBM Fez Open Plan N15 Shor factor-recovery study](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md) succeeded with N15, a=2, but this particular modulus has order 4 unchanged by cubing and does not demonstrate Dark Star cubic preconditioning.

Our prior [N35 full-register public permutation preflight](QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_RESULT.md) achieved ~61% fewer *compiled target-native* CZ/depth when public a=2 was cubed to a³=8 (multiplicative order 12→4), but all four arms failed frozen real QPU criterion native CZ≤800 and depth≤2000. It is an exponential full-truth-table permutation synthesizer. The next [N35 algebraically generic n-bit arithmetic method](QRR_N35_ARITHMETIC_REPLACEMENT_RESULT.md) reduced CZ internally about 50% with cubing, but eager nested controlled IntegerComparator and Draper QFTAdder made four-round circuits enormous (base2 1.73m CZ, cube8 0.86m CZ), and the primary device gate failed.

This preregistered [single-KERNEL-only explicit Toffoli/ripple experiment](QRR_N35_TOFFOLI_RIPPLE_SINGLE_MULTIPLIER_PREREG.md) commit **`8e4031f2ca9e4efac853058d45625a1d8807106f`** was frozen BEFORE running target-native compilations. This experiment isolates ONE controlled multiplication by base a=2 and cube a³=8, **not** a complete 4bit Shor QPE circuit. N35 trivially factors classically 5×7; the true order label r=12→4 is not used to compile the multiplier.

## Actual full public arithmetic from explicit primitive gates

Implementation [`hardware/qrr_n35_single_modmul_ripple_toffoli.py`](../hardware/qrr_n35_single_modmul_ripple_toffoli.py) builds one controlled reversible unitary: for every y∈[0,63] and control c, `|c>|y>|0...0>→|c>|a^c·y mod35>|0...0>` if y<35, otherwise identity. Input y is a full six-bit register; no precomputed 12-state orbit, private primes, true order, image watermark tricks, or oracle knowledge.

- **Elementary reversible gates only:** X, CNOT and CCX/Toffoli, with explicit clean v-chain fan-in for multi-controls. No QFT adder, controlled annotated arithmetic, general multi-controlled black box, precomputed order-gate or hidden factoring trick.
- Comparison `x>=t` uses n=6 clean carries for the bitwise carry recurrence of unsigned `x+(64-t)`; high carry is XORed into flag with optional controls and all carry ancillas are uncomputed by reversing the same gates.
- An in-place controlled `+k mod64` is built out of descending-order controlled suffix increments with explicit Toffoli chains. A reversible public `+k mod35` uses wrap-comparison, conditional add k, conditional subtract35, and output-value recomputation of the wrap predicate to reset the flag.
- Controlled multiplication uses six source-bit-weighted modular additions into a clean 6-bit accumulator, coherent controlled SWAP, then six inverse-weighted modular subtractions to erase accumulator. The validity predicate `work<35` ensures invalid basis states y≥35 remain identical.
- Uses 30 application/logical qubits (one control, six work, six accumulator, two flags, six carry, nine clean v-chain scratch), compared to 26/29 logical qubits for prior 4bit stage-recycled/stage-wide arithmetic method. **Different tasks and register layouts**—do not imply this single kernel saves logical width.
- **EXHAUSTIVE actual emitted gate-level ideal-basis equivalence**: the original Qiskit circuit is interpreted directly gate-by-gate on **128/128** combinations of all 64 y and c∈{0,1} for both bases. Verifies target exact multiplication, unchanged control, every accumulator, flag, carry and scratch qubit back to |0>, identity on invalid y, and no nonprimitive gates. This is more informative than a separate classical arithmetic shadow model, though not a quantum-noise measurement or general formally verified arbitrary-quantum-state proof.

## Source CI, credential-only rerun and independently preserved original numerical outputs

Initial [CI **38996961616**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996961616) already passed both 128/128 gate-basis semantic checks, but the IBM backend metadata connection failed on GitHub because the script requested a **locally saved** account instead of using the existing encrypted GitHub `IBM_QUANTUM_API_KEY` secret. No scientific results/algorithms were altered. Only backend read-only authentication was corrected (commit `1e17faef6abeddbeeb2b9d8d6236ca900defce7e`), with no credential ever emitted to logs.

Second unmodified-method [CI **38997012532**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38997012532): **2/2 successful** primitive-source/exhaustive-equivalence tests and read-only IBM Fez-native Qiskit transpiles, using Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, optimization level1, fixed seed8776, no Sampler/Estimator/Runtime submit. Both result JSONs include exact original primitive source gate counts, native CZ/depth/size/ops, logical width, backend device width and full actual gate-proof receipts.

[Independent unchanged-original receipt validation/preservation CI **38997085447**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38997085447): **SUCCESS**, downloaded the two source-run artifacts without recompilation, independently checked all 128-state gate proofs, valid/invalid residue semantics, zeroed scratch, backend/seed, original compiled native op counts, two predeclared QPU-gate failures and absence of any device job. Preserved original JSON bytes in [base2](../results/ibm_shor35_ripple_toffoli_kernel/qrr_n35_toffoli_ripple_single_mul_base2.json) and [cube8](../results/ibm_shor35_ripple_toffoli_kernel/qrr_n35_toffoli_ripple_single_mul_base8.json), commit `b064ced6f503b499457d9e01e30f130dc5bb7fb5`.

## Full original IBM Fez target-compiler result — ONE controlled multiplier only

| Frozen single controlled full-register reversible mod-mul kernel | Public a=2 | Public cube a³=8 |
|---|---:|---:|
| Exhaustive **actual emitted gate** input/control cases | 128/128 PASS | 128/128 PASS |
| All 22 aux bits (acc/flags/carry/scratch) returned to zero | **yes** | **yes** |
| Primitive X/CX/CCX total | **1,964** | **2,062** |
| Logical circuit qubits | 30 | 30 |
| **IBM Fez-target compiled native CZ** | **27,929** | **29,822** |
| **IBM Fez-target compiled depth** | **59,947** | **63,922** |
| IBM Fez target hardware device width | 156 | 156 |
| Native CZ ≤800 and depth ≤2,000 | **FAIL** | **FAIL** |
| Physical QPU submissions | 0 | 0 |

**Important negative mechanism finding:** On a single controlled multiplication, cube base8 is about **6.78% MORE native CZ** and **6.63% GREATER depth** than base2 in this implementation. The theoretical order reduction 12→4 does not make a solitary modular multiplier automatically cheaper! The cubic transformation's favorable result in earlier 4-round circuits primarily comes from exponent-power schedule `[2,4,16,11]→[8,29,1,1]`: **two entire identity rounds** may be skipped. If the number of QPE modular-power rounds or phase bits is fixed, that savings has to outweigh any cost of the nontrivial cube multipliers.

The 27.9k/29.8k native CZ counts are much smaller than the prior *four-round* QFT-adder circuits' 0.86–1.73m CZ, but those are DIFFERENT work scopes (one controlled multiply vs four). Thus do NOT quote a naive speedup factor from direct division, or assume all four new kernels have the same resource cost—each multiplier's constant changes.

**Physical feasibility primary gate FAILS:** Even one multiplier, using pure native-lowerable primitive arithmetic, requires 27,929 to 29,822 CZ and depth 59,947 to 63,922, over **34×** the CZ threshold and **29×** the depth limit. These heuristic hardware limits are not a full calibrated error budget, but they are the frozen go/no-go rule, so the free Open Plan device was NOT contacted to submit any job. This is a verified architectural simplification and mathematical semantics milestone, NOT actual quantum factoring progress on larger keys or Dark Star QPU execution.

## Honest roadmap

Further optimization should address **algorithmic modular arithmetic**, not just replace abstract gates with explicit Toffoli decomposition. Viable topics: purpose-designed carry reuse, constant-specific bit sparse arithmetic, controlled vs uncontrolled recurrence factorization, reducing repeated three-way controls and fan-in, and compiling all 4 public modular powers after independent one-round resource validation. The current single-multiplier gate cannot meet the Open Plan hardware threshold. Do not hide that negative by switching to order-encoded/orbit-compiled toy circuits without labeling them. A separate real-QPU cubic experiment still requires an actual feasible matched plain/cube factorizations and explicit verified Open Plan-only authorization.

Both the previous genuine real N15 phase-recycling hardware achievement and the more conditional/negative 22bit public-key QPE model history remain intact and documented.
