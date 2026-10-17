#!/usr/bin/env python3
"""Zero-QPU N35 real-ISA compile of arithmetic-controlled multiplier; no orbits.

Reuses CaMaLabs generic_modarith_shor arithmetic builder with eager arithmetic
Qiskit compatibility lowering, and prunes ONLY public multipliers ==1 (mod N).
No Shor order input, no orbit lookup, no QPU Runtime primitive.
Lead Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import json,math,time,traceback
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# Import establishes explicit IntegerComparator/DraperQFTAdder implementations
# of the same old full-register reversible-modarith construction.
import ibm_shor35_generic_modarith_preflight_explicit as explicit
import generic_modarith_shor as gm
import ibm_shor35_matched as shor

N=35
BITS=4
REVISION="qrr-n35-public-reversible-shift-add-cube-v1-20261016"
OUTDIR=Path("results/ibm_shor35_modarith_identity_pruned")

_orig_controlled_mul=gm.append_controlled_modmul_constant
def public_identity_pruned_mul(qc,*,multiplier,modulus,**kwargs):
    if int(multiplier)%int(modulus)==1:
        # A permutation U(x)=x on the entire residue register, controlled or
        # not, is trivially no-op; no secret multiplicative order is consulted.
        return
    return _orig_controlled_mul(qc,multiplier=multiplier,modulus=modulus,**kwargs)

gm.append_controlled_modmul_constant=public_identity_pruned_mul

def brute_order(a,n):
    x=1
    for r in range(1,n*n+1):
        x=x*a%n
        if x==1:return r
    raise RuntimeError("No order")


def audit_setup(args):
    assert args.backend=="ibm_fez"
    assert args.base in (2,8)
    assert args.kind in ("recycled","wide")
    assert args.phase_bits==4
    assert args.optimization_level==1 and args.seed==8776
    assert pow(2,3,N)==8 and brute_order(2,N)==12 and brute_order(8,N)==4
    assert math.gcd(28,35)==7 and math.gcd(30,35)==5
    multipliers=[pow(args.base,1<<k,N) for k in range(BITS)]
    assert multipliers==([2,4,16,11] if args.base==2 else [8,29,1,1]),multipliers
    return multipliers


def save(receipt,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(receipt,indent=2,default=str)+"\n")


def run(args):
    mult=audit_setup(args)
    destination=OUTDIR/f"qrr_n35_public_modarith_{args.kind}_{'plain' if args.base==2 else 'cube'}.json"
    record=dict(revision=REVISION,experiment="N35 public-identity-pruned arithmetic-based controlled modular multiplication",
        date_utc=datetime.now(timezone.utc).isoformat(),
        lead="Chase Lunsford / CaMaLabs",
        preregistration="docs/QRR_N35_ARITHMETIC_REPLACEMENT_PREREG.md",
        source="hardware/generic_modarith_shor.py (existing public n-bit shift-add compute/swap/uncompute)",
        compiler_compatibility="hardware/ibm_shor35_generic_modarith_preflight_explicit.py (eager controlled IntegerComparator/DraperQFTAdder)",
        public_only_optimization="elide entire controlled U when pow(base,2**k,N)==1; no private order used",
        backend=args.backend,N=N,base=args.base,phase_bits=BITS,architecture=args.kind,
        phase_power_multipliers=mult,
        identity_rounds=[k for k,m in enumerate(mult) if m==1],
        nontrivial_rounds=sum(x!=1 for x in mult),
        validation_only_order=brute_order(args.base,N),
        true_order_used_in_circuit_construction=False,
        orbit_encoding_used=False,
        explicit_64_state_permutation_synthesis_used=False,
        semantic_reference_verified=False,
        optimization_level=args.optimization_level,seed_transpiler=args.seed,
        qpu_submitted=False,qpu_jobs_submitted=0,
        status="STARTED",success=False,
        frozen_hardware_heuristic=dict(max_cz=800,max_depth=2000,hardware_feasible=False))
    save(record,destination)
    # Fresh public classical verification, no order used by circuit construction.
    sem=gm.semantic_self_test(N,args.base,BITS)
    assert sem["pass"] and sem["order_used_in_circuit_construction"] is False
    assert sem["controlled_modmul_cases"]>=4*2*(1<<N.bit_length())
    record["semantic_reference_verified"]=True
    record["semantic_self_test"]=sem
    record["logical_resources"]=asdict(gm.arithmetic_resources(N,args.base,BITS))
    def measure(qc, qubit, bit):
        shor.ibm_base.mid_measure(qc,qubit,bit,measure_2)
    print("ORIGINAL FULL n-BIT ARITHMETIC SEMANTICS VERIFIED",args.kind,args.base,
          "multipliers",mult,"pruned identity rounds",record["identity_rounds"],flush=True)
    save(record,destination)
    service=shor.ibm_base.make_service()
    required=record["logical_resources"]["wide_logical_qubits" if args.kind=="wide" else "recycled_logical_qubits"]
    backend=shor.ibm_base.select_backend(service,required,args.backend)
    measure_2=shor.ibm_base.backend_has_measure2(backend)
    assert backend.name==args.backend
    record["backend_name_resolved"]=backend.name
    record["backend_qubits"]=backend.num_qubits
    record["mid_measure_supported"]=bool(measure_2)
    if args.kind=="recycled" and not measure_2:
        raise RuntimeError("IBM Fez backend lacks measure_2 needed for recycled circuit")
    if args.kind=="recycled":
        qc=gm.build_recycled_order_finder(N,args.base,BITS,mid_measure=measure)
    else:
        qc=gm.build_wide_order_finder(N,args.base,BITS)
    assert qc.num_qubits==required
    record["source_logical_qubits"]=qc.num_qubits
    record["highlevel_ops"]=dict(qc.count_ops())
    record["highlevel_size"]=qc.size()
    record["highlevel_depth"]=qc.depth()
    record["status"]="COMPILING"
    save(record,destination)
    pm=generate_preset_pass_manager(backend=backend,
       optimization_level=args.optimization_level,seed_transpiler=args.seed,
       qubits_initially_zero=True)
    start=time.perf_counter()
    compiled=pm.run(qc)
    elapsed=time.perf_counter()-start
    ops={str(k):int(v) for k,v in compiled.count_ops().items()}
    cz=int(ops.get("cz",0))
    depth=int(compiled.depth())
    width=int(compiled.num_qubits)
    assert width>=qc.num_qubits
    stats=dict(native_cz=cz,native_depth=depth,native_size=int(compiled.size()),
        compiled_device_width=width,compiled_native_ops=ops,
        compile_seconds=elapsed,logical_qubits=qc.num_qubits,
        max_heuristic_cz=800,max_heuristic_depth=2000,
        native_hardware_feasibility_pass=bool(cz<=800 and depth<=2000))
    record.update(status="COMPILE_SUCCESS",success=True,stats=stats,
        frozen_hardware_heuristic=dict(max_cz=800,max_depth=2000,
        hardware_feasible=stats["native_hardware_feasibility_pass"]))
    save(record,destination)
    print("DONE arithmetic N35",args.kind,"base",args.base,
          "CZ",cz,"DEPTH",depth,"LOGICAL_QUBITS",qc.num_qubits,
          "FROZEN_HARDWARE_GATE",stats["native_hardware_feasibility_pass"],
          "NO QPU",str(destination),flush=True)
    return 0


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--backend",default="ibm_fez")
    parser.add_argument("--base",type=int,required=True,choices=[2,8])
    parser.add_argument("--kind",required=True,choices=["wide","recycled"])
    parser.add_argument("--phase-bits",type=int,default=4)
    parser.add_argument("--optimization-level",type=int,default=1)
    parser.add_argument("--seed",type=int,default=8776)
    args=parser.parse_args()
    # Even compiler errors produce auditable receipts, NO runtime submissions.
    destination=OUTDIR/f"qrr_n35_public_modarith_{args.kind}_{'plain' if args.base==2 else 'cube'}.json"
    try:
        raise SystemExit(run(args))
    except (KeyboardInterrupt,SystemExit):
        raise
    except Exception as exc:
        record=json.loads(destination.read_text()) if destination.exists() else {}
        record.update(status="COMPILE_OR_SEMANTIC_FAILURE",success=False,
            failure_class=type(exc).__name__,
            failure_message=str(exc)[:650],
            qpu_submitted=False,qpu_jobs_submitted=0)
        save(record,destination)
        print("ZERO-QPU N35 ARITHMETIC FAILURE",type(exc).__name__,str(exc)[:350],flush=True)
        raise SystemExit(1)
