#!/usr/bin/env python3
import json
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService(plans_preference=["open"], region="us-east")

print("=== IBM QUANTUM OPEN PLAN PREFLIGHT ===")
try:
    print("Active instance:")
    print(json.dumps(service.active_instance(), indent=2, default=str))
except Exception as exc:
    print("Active instance unavailable:", exc)

try:
    print("\nUsage:")
    print(json.dumps(service.usage(), indent=2, default=str))
except Exception as exc:
    print("Usage unavailable:", exc)

print("\nFinding operational dynamic-circuit QPUs...")
backends = service.backends(
    operational=True,
    simulator=False,
    dynamic_circuits=True,
)

if not backends:
    raise SystemExit("No Open Plan dynamic-circuit QPUs are currently available.")

rows = []
for b in backends:
    try:
        pending = b.status().pending_jobs
    except Exception:
        pending = None
    try:
        has_measure2 = "measure_2" in b.supported_instructions
    except Exception:
        has_measure2 = False
    rows.append((b.name, b.num_qubits, has_measure2, pending))

rows.sort(key=lambda r: (r[3] is None, r[3] if r[3] is not None else 10**9))

print("\nAvailable dynamic-circuit backends:")
for name, nq, m2, pending in rows:
    print(
        f"  {name:24s} qubits={nq:3d} "
        f"measure_2={'yes' if m2 else 'no ':3s} pending={pending}"
    )

m2_backends = [r for r in rows if r[2]]
if m2_backends:
    print("\nRecommended for our 6C2Q test:", m2_backends[0][0])
else:
    print("\nNo current backend reports measure_2; ordinary mid-circuit measure can still work.")

print("\nPREFLIGHT PASSED. No QPU job was submitted.")
