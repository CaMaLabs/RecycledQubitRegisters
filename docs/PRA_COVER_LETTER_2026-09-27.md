27 September 2026

Editors  
Physical Review A

Dear Editors,

Please consider the manuscript **“Dynamic phase-register recycling and hardware-aware placement in compiled Shor order finding on superconducting quantum processors”** as a Regular Article in *Physical Review A*.

The manuscript reports experimental quantum-computing results for a compiled `N=35`, `a=2`, `r=12` Shor order-finding benchmark on IBM superconducting hardware. It compares an eight-qubit coherent phase register with a one-ancilla dynamic recycled phase register while matching the compiled work-register problem, phase precision, shot count, initial work-register placement within each comparison, and classical post-processing.

The principal result is not a claim that recycled circuits are universally superior. On IBM Fez, the recycled architecture repeatedly preserved substantially more order-finding signal than the matched wide architecture while using 5 rather than 12 simultaneous logical qubits. A subsequent hardware-aware placement search improved the measured recycled distribution while preserving the strict direct-order signal. Same-job cross-backend controls on IBM Marrakesh then showed that the wide-versus-recycled ranking changes with placement and calibration window. The combined result is therefore an experimentally grounded architecture × placement × backend interaction, with simultaneous coherent width acting as one hardware resource among several.

We believe the work fits PRA’s Quantum Technologies / Quantum Information scope because it concerns quantum-computation architectures and implementations, dynamic-circuit control, hardware-aware compilation, and experimental benchmarking on superconducting processors.

The manuscript is deliberately conservative about scope. It uses an exact compiled four-qubit affine representation of the twelve-state modular orbit and is **not** a scalable general-purpose Shor implementation or a claim of quantum advantage. It also retains failed and null experiments, reports analytic uniform-output baselines under the same classical post-processing, and distinguishes shot-noise calculations from full hardware uncertainty.

Code, benchmark definitions, and result records are publicly available at:

https://github.com/CaMaLabs/RecycledQubitRegisters

A public preprint may also be deposited on Zenodo before or during review in accordance with APS preprint policy.

**AI-use disclosure:** OpenAI ChatGPT, GPT-5.6 Sol, was used substantively for research organization, literature-search assistance, software-development support, statistical cross-checking, and drafting/editing portions of the manuscript. The author directed the work through explicit technical prompts and reviewed the resulting claims against the repository’s source code, hardware result artifacts, analytic calculations, and cited literature. The author remains solely responsible for the scientific content, interpretation, and submission.

Thank you for your consideration.

Sincerely,

Chase Lunsford  
CaMaLabs
