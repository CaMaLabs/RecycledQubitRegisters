# K001 — Google Quantum AI Verifiable Quantum Circuit Compilation

**Status: Bootstrap prepared; no candidate benchmarked and no submission made.**

This is a competition-specific, independently verifiable research track. It does not claim that A110's factoring multiplier results translate directly to Google's kickmix benchmarks.

## Private official data

Participation and competition-rules acceptance are confirmed by the participant. Run `bash competition/k001/bootstrap.sh` from a checked-out copy of this branch. The script uses Kaggle's authenticated command-line client to download the competition archive to `competition/k001/private/downloads/`, unpacks it only to `competition/k001/private/official/`, and pulls the official metric notebook to `competition/k001/private/metric/` when accessible. All official assets are excluded from Git. Kaggle credentials and competition data must never be placed in public GitHub commits.

The script writes an **inventory only** to `competition/k001/k001_environment_report.json`, listing filenames/sizes, archive SHA-256, and interpreter/environment metadata. This report is a diagnostic that can be shown to the assistant to determine the official gate schema and verifier entry points. It is not a Kaggle submission.

Next stages:
- K002: inspect kickmix API, supported gates, baseline circuits, and official scoring; no assumptions on metric or task representation.
- K003: translate A110's proven commutation/involution cancellation to supported kickmix gate families; explicitly account for phases and measurement-based uncomputation.
- K004: run official task verifiers, score against official baseline, and package all **three** required benchmark outputs with full metric preflight.
- K005: submit via authenticated Kaggle CLI after a genuine verified result is available.

Do not republish official binary circuits, source verifiers, competition data, or metric kernel contents. Do not claim official score from local calculations.
