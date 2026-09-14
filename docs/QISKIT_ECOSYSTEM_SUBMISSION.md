# Qiskit Ecosystem submission draft

This file mirrors the current fields in the Qiskit Ecosystem submission form and is intended to make the external submission reproducible.

## Project name

RecycledQubitRegisters

## Description

Research toolkit for dynamic phase-register recycling, QPE/Shor benchmarks, and hardware-aware placement with Qiskit.

## Contact email

Leave blank unless a public project contact email is desired.

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

Leave blank for now.

## Documentation

https://github.com/CaMaLabs/RecycledQubitRegisters/tree/main/docs

## Packages

Leave blank for now; the project is currently distributed as source rather than as a published package.

## Reference paper

Leave blank until the preprint is posted publicly. The repository currently contains `docs/QRR_SHOR35_PREPRINT_DRAFT.md` as a working preprint draft.

## Code of Conduct

Check: **I agree to follow the Qiskit Code of Conduct**.

## Why this qualifies

RecycledQubitRegisters builds directly on Qiskit and Qiskit IBM Runtime. Its hardware benchmarks construct and transpile Qiskit circuits, use Qiskit dynamic-circuit features including mid-circuit measurement/reset/classical feed-forward, and execute through the V2 primitive stack (`SamplerV2`). The project is tested with Qiskit 2.5.x and `qiskit-ibm-runtime` 0.47.x.

The project is licensed under Apache-2.0 and has adopted the Qiskit Code of Conduct.

## Suggested reviewer note

RecycledQubitRegisters is an experimental research toolkit exploring whether iterative/dynamic phase-register recycling and calibration-aware placement can reduce simultaneous coherent width while preserving useful phase-estimation and compiled Shor order-finding signal on present superconducting hardware. The repository includes exact simulation checks, matched same-job hardware controls, explicit uniform-output baselines, negative/null results, and backend-specific placement experiments. The strongest current benchmark is a compiled `N=35`, `a=2`, `r=12` order-finding experiment tested on IBM Fez and Marrakesh. The project does not claim a scalable general-purpose Shor implementation or a practical cryptographic attack.

## Suggested Qiskit Slack post

I’ve open-sourced **RecycledQubitRegisters**, an experimental Qiskit project for dynamic phase-register recycling and hardware-aware placement. It compares conventional wide QPE/Shor circuits with iterative circuits that reuse one phase ancilla through mid-circuit measurement, reset, and feed-forward. The current compiled `N=35`, `a=2`, `r=12` benchmark has matched real-hardware data on Fez and Marrakesh, including same-job layout A/B controls and explicit uniform-output baselines. I’d especially value feedback on the dynamic-circuit methodology, placement controls, and interpretation of the backend-dependent results: https://github.com/CaMaLabs/RecycledQubitRegisters

## Submission link

Use the official Qiskit Ecosystem submission form:

https://qisk.it/add-to-ecosystem
