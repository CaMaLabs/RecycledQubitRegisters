# Publication route — RecycledQubitRegisters Shor-35 paper

**Prepared:** 27 September 2026  
**Manuscript:** `docs/QRR_SHOR35_PREPRINT_2026-09-27.md`

## Objective

Publish the current `N=35`, `a=2`, `r=12` dynamic phase-register recycling result in two stages:

1. **Public preprint with DOI:** Zenodo.
2. **Peer-reviewed journal submission:** Physical Review A (PRA), standard publication route.

This route is intentionally chosen so that arXiv endorsement is not a blocking dependency.

## Why Zenodo first

Zenodo is a general-purpose research repository operated for research-output preservation. A published record is assigned a DataCite DOI automatically. The manuscript can therefore become immediately citable as a preprint while journal peer review proceeds independently.

Zenodo deposit fields to use:

- **Resource type:** Publication / Preprint (or the closest available preprint subtype in the current deposit UI)
- **Title:** Dynamic phase-register recycling and hardware-aware placement in compiled Shor order finding on superconducting quantum processors
- **Creator:** Chase Lunsford
- **Publisher:** Zenodo
- **Publication date:** date of deposit
- **Access:** Open
- **License:** CC BY 4.0 unless a later journal-specific constraint requires a different preprint license
- **Version:** 1.0
- **Language:** English
- **Related identifier:** `https://github.com/CaMaLabs/RecycledQubitRegisters`
- **Keywords:** quantum computing; Shor algorithm; quantum phase estimation; dynamic quantum circuits; qubit recycling; superconducting quantum computing; IBM Quantum; hardware-aware compilation; quantum benchmarking

### Zenodo description / abstract

Dynamic quantum circuits can exchange simultaneous coherent width for mid-circuit measurement, reset, and real-time classical feed-forward. This preprint reports replicated `r=12` order recovery for a compiled `N=35`, `a=2` Shor order-finding instance on IBM superconducting hardware using a dynamically recycled phase register, together with matched wide-register controls and cross-backend hardware-aware placement experiments on IBM Fez and Marrakesh. The results show that reduced simultaneous coherent width can preserve useful order information, but also that the wide-versus-recycled ranking depends strongly on physical placement, backend, and calibration state. The work is a compiled-orbit hardware benchmark and is not a scalable general-purpose Shor implementation.

## Why Physical Review A

PRA explicitly covers quantum information science, quantum algorithms, quantum computation architectures/implementations, quantum hardware, and quantum control/feedback. The manuscript is an experimental quantum-computation / hardware-co-design paper rather than a broad algorithmic claim.

PRA accepts direct electronic manuscript submission; arXiv is not a prerequisite. APS permits preprints to be posted on public platforms. PRA is a hybrid journal, so open-access APC payment is optional rather than required for standard publication.

### Suggested PRA section

Primary: **A-3E — Quantum Technologies**

Relevant topics:

- quantum computation and simulation (architectures and implementations)
- quantum hardware: engineering and technologies
- quantum control and feedback

Secondary possible section: **A-2E — Quantum Information Science**, especially quantum algorithms, gates, and error correction / quantum information processing.

## Submission framing

### Recommended article type

Regular Article.

### Central claim

The paper should not be framed as “first to factor 35.” The defensible claim is:

> We report replicated recovery of `r=12` order information for a compiled `N=35`, `a=2` Shor instance on IBM superconducting hardware using a dynamically recycled phase register, together with cross-backend controls showing that the benefit depends strongly on physical placement and calibration.

### Qualified priority statement

> To our knowledge, this is the first reported successful experimental recovery of the `r=12` Shor order for `N=35`, `a=2` on gate-based superconducting quantum hardware.

Keep “to our knowledge.” Re-run the literature search immediately before submission.

### Claims to avoid

- first quantum factorization of 35
- first Shor experiment for 35
- first qubit-recycling Shor experiment
- first dynamic-circuit Shor experiment on superconducting hardware
- scalable Shor implementation
- quantum advantage
- universal superiority of recycled circuits over wide circuits

## Evidence package

Core repository records:

- `docs/QRR_SHOR35_PREPRINT_2026-09-27.md`
- `docs/N35_NOVELTY_AUDIT_2026-09-14.md`
- `results/hardware/SHOR35_AFFINE_HARDWARE.md`
- `results/hardware/SHOR35_OPTIMIZED_HARDWARE.md`
- `results/hardware/SHOR35_MARRAKESH_CROSS_BACKEND.md`
- `results/hardware/SHOR35_MARRAKESH_LAYOUT_OPTIMIZATION.md`
- `results/hardware/SHOR35_MARRAKESH_LAYOUT_AB.md`

## PRA cover-letter points

Keep the cover letter short. It should state:

1. The manuscript reports experimental superconducting-hardware results for compiled `N=35`, `a=2`, `r=12` Shor order finding.
2. It compares a conventional eight-qubit phase register with a one-ancilla dynamic recycled phase register under matched controls.
3. It includes independent Fez replication and same-job cross-backend Marrakesh layout controls.
4. It explicitly reports null/negative results and analytic random-output baselines.
5. The principal conclusion is an architecture × placement × backend interaction, not a universal recycled-over-wide advantage.
6. Code and result records are public and reproducible.

## Submission blockers still requiring account-level action

The research package can be prepared without additional endorsement. The following actions are inherently account-level and cannot be replaced by email:

- logging into Zenodo and pressing the final **Publish** control;
- confirming the Zenodo deposit metadata/license in the user's account;
- logging into the APS submission system;
- accepting APS authorship/copyright/ethics certifications;
- selecting final journal submission declarations and pressing the final submit control.

These are author attestations rather than scientific endorsements.

## Current status

- Cross-backend manuscript drafted: **yes**
- Current literature boundary re-checked: **yes, preliminary 27 Sep 2026**
- Zenodo DOI route verified: **yes**
- PRA scope fit verified: **yes**
- arXiv required for PRA: **no**
- mandatory PRA standard-publication APC: **no**
- submission PDF/REVTeX package: **next**
- Zenodo DOI published: **pending account-level deposit**
- PRA manuscript submitted: **pending final package and account-level attestations**
