# Qiskit Ecosystem membership and submission record

## Membership status

**Accepted.** RecycledQubitRegisters was merged into the Qiskit Ecosystem on 2026-09-15 through [Qiskit/ecosystem#1375](https://github.com/Qiskit/ecosystem/pull/1375).

Official Ecosystem member metadata:

- project: `RecycledQubitRegisters`
- category: `Tooling`
- maturity: `experimental`
- interfaces: `Python`, `Command-line interface (CLI)`
- member UUID: `68e87191-fd1c-46d7-ba88-b8bcc3a67c20`

Official badge markdown:

```markdown
[![Qiskit Ecosystem](https://qisk.it/e-68e87191)](https://qisk.it/e)
```

Membership indicates that the project is part of the Qiskit Ecosystem; it should not be interpreted as independent validation or endorsement of the repository's research claims.

---

The remainder of this file preserves the submitted project information for reproducibility.

## Project name

RecycledQubitRegisters

## Description

Research toolkit for dynamic phase-register recycling, QPE/Shor benchmarks, and hardware-aware placement with Qiskit.

## Contact email

Left blank; no public project contact email was supplied.

## Category

Tooling

## Labels

- research
- benchmarking
- circuit building
- circuit optimization
- quantum information

## Interface/API

- Python
- Command-line interface (CLI)

## Stability and support expectations

experimental

## GitHub repository

https://github.com/CaMaLabs/RecycledQubitRegisters

## Home page

No separate project home page was supplied at submission time.

## Documentation

https://github.com/CaMaLabs/RecycledQubitRegisters/tree/main/docs

## Packages

No package registry entry was supplied; the project is currently distributed as source rather than as a published package.

## Reference paper

No public reference paper was supplied at submission time. The repository contains `docs/QRR_SHOR35_PREPRINT_DRAFT.md` as a working preprint draft.

## Code of Conduct

Accepted: **I agree to follow the Qiskit Code of Conduct**.

## Why this qualifies

RecycledQubitRegisters builds directly on Qiskit and Qiskit IBM Runtime. Its hardware benchmarks construct and transpile Qiskit circuits, use Qiskit dynamic-circuit features including mid-circuit measurement/reset/classical feed-forward, and execute through the V2 primitive stack (`SamplerV2`). The project is tested with Qiskit 2.5.x and `qiskit-ibm-runtime` 0.47.x.

The project is licensed under Apache-2.0 and has adopted the Qiskit Code of Conduct.

## Reviewer note used for submission

RecycledQubitRegisters is an experimental research toolkit exploring whether iterative/dynamic phase-register recycling and calibration-aware placement can reduce simultaneous coherent width while preserving useful phase-estimation and compiled Shor order-finding signal on present superconducting hardware. The repository includes exact simulation checks, matched same-job hardware controls, explicit uniform-output baselines, negative/null results, and backend-specific placement experiments. The strongest current benchmark is a compiled `N=35`, `a=2`, `r=12` order-finding experiment tested on IBM Fez and Marrakesh. The project does not claim a scalable general-purpose Shor implementation or a practical cryptographic attack.

## Suggested Qiskit Slack introduction

I’ve open-sourced **RecycledQubitRegisters**, an experimental Qiskit project for dynamic phase-register recycling and hardware-aware placement. It compares conventional wide QPE/Shor circuits with iterative circuits that reuse one phase ancilla through mid-circuit measurement, reset, and feed-forward. The current compiled `N=35`, `a=2`, `r=12` benchmark has matched real-hardware data on Fez and Marrakesh, including same-job layout A/B controls and explicit uniform-output baselines. I’d especially value feedback on the dynamic-circuit methodology, placement controls, and interpretation of the backend-dependent results: https://github.com/CaMaLabs/RecycledQubitRegisters

## Original submission link

The project was nominated through the official Qiskit Ecosystem submission process:

https://qisk.it/add-to-ecosystem
