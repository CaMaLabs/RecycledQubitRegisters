# A22 N35 matched synthetic phase and public recovery — 2026-10-30

User-run `hardware/qrr_a22_n35_matched_pipeline_bridge.py --upstream /tmp/qrr-indie-quaspy --shots 128` after precision contract fix. `PASS_MATCHED_SYNTHETIC_ONLY`, 0 QPU jobs. Each arm has 128 independently sampled synthetic ideal QPE frequencies drawn with true order used **only by sampler**, not public recovery.

|Base|Phase bits|CF verified /128|Quaspy verified /128|Quaspy eligibility|CF pow calls|Quaspy pow calls|
|---:|---:|---:|---:|---|---:|---:|
|2|4|0|N/A|ineligible 128|143|0|
|2|6|17|N/A|ineligible 128|130|0|
|2|8|36|128|eligible|155|1408|
|8|4|59|N/A|ineligible 128|147|0|
|8|6|62|N/A|ineligible 128|162|0|
|8|8|64|128|eligible|161|1024|

None censored or work limited. `0` for Quaspy at 4/6 bits means ineligible, not failed recovery. Quaspy requires phase bits strictly larger than N bit length (6), max twice. This is N35 ideal synthetic recovery, not actual compiled circuit sampling nor a joint Dark Star preconditioning/Quaspy experiment. Performance on small N35 does not transfer to RSA sizes. Still unproven: full end-to-end generated phase distribution, precise classical preprocessing accounting, broad heldout cohort, actual hardware feasibility.
