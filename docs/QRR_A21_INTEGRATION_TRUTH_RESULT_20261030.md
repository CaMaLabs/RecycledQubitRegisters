# A21 truth-in-integration audit — user execution 2026-10-30

`python hardware/qrr_a21_integration_truth_audit.py` => `PASS_WITH_INTEGRATION_GAPS`, zero QPU jobs.

Verified code connection: frozen selected arithmetic + one-phase-qubit dynamic N35, exact 32-to-23-qubit instruction-identical scratch removal. Offline Fez compilation and placement analysis is separate from actual shot outputs. Dark Star order preconditioning was validated on N209/713/781 staged resource models; Quaspy was validated with a different synthetic semiprime holdout. The rejected A20 direct-cycle multiplier is NOT integrated.

Unresolved: G1 no same-cohort full pipeline; G2 incomparable moduli and error sources; G3 no total classical-work denominator; G4 current N35 Fez gate fails hard threshold; G5 original periodic prime-table/pruning provenance and activation unverified.

Do not combine headline resource percentages across incomparable cohorts. Next audit must begin with identical N35 modulus/base/phase outputs and track preprocessing cost. Never use hidden order or factors as solver input. This audit is static code/provenance checking, not a new full algorithm success.
