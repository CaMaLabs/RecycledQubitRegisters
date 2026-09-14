#!/usr/bin/env python3
import getpass
from qiskit_ibm_runtime import QiskitRuntimeService

print("IBM Quantum Open Plan credential setup")
print("Your API key will not be echoed.")
token = getpass.getpass("IBM Quantum API key: ").strip()
if not token:
    raise SystemExit("No API key entered.")

crn = input(
    "Open Plan instance CRN (optional; press Enter to auto-select Open Plan): "
).strip()

kwargs = dict(
    token=token,
    set_as_default=True,
    overwrite=True,
)

if crn:
    kwargs["instance"] = crn
else:
    # Explicitly exclude paid plans when auto-selecting.
    kwargs["plans_preference"] = ["open"]
    kwargs["region"] = "us-east"

QiskitRuntimeService.save_account(**kwargs)

# Verify immediately without submitting a workload.
if crn:
    service = QiskitRuntimeService(instance=crn)
else:
    service = QiskitRuntimeService(plans_preference=["open"], region="us-east")

print("\nCredentials saved and authentication succeeded.")
try:
    print("Active instance:", service.active_instance())
except Exception as exc:
    print("Active instance: unavailable:", exc)

try:
    print("Usage:", service.usage())
except Exception as exc:
    print("Usage: unavailable:", exc)

print("\nNo QPU job was submitted.")
