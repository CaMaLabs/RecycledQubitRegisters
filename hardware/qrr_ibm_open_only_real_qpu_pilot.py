#!/usr/bin/env python3
"""One-shot REAL QPU small-N15 matched Shor hardware pilot, verified IBM OPEN only.

NO paid-plan override, fallback, or simulator. Mirrors existing Shor15
modular-multiplication circuit; explicitly NOT a Dark Star cube speedup test.
Maximum two four-bit-phase circuits at 64 shots each, one Runtime Sampler job.
Research lead Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import json,os,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
import ibm_shor15_hardware as shor
from ibm_runtime_guard import assert_open_plan_submission,RuntimePlanGuardError

OUT=Path("results/real_qpu/qrr_n15_open_only_real_qpu_pilot.json")
MAX_SHOTS=64
MAX_RUNTIME_SEC=30
MAX_COMPILED_DEPTH=2000
MAX_NATIVE_2Q=800


def save(obj):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(obj,indent=2,default=str)+"\n")


def blocked(obj,reason):
    obj.update(status="PREFLIGHT_BLOCKED",submission_performed=False,job_id=None,
       block_reason=reason)
    save(obj)
    print("NO QPU JOB SUBMITTED. PREFLIGHT BLOCKED:",reason,flush=True)
    return 0


def main():
    out=dict(experiment="qrr_shor15_matched_real_qpu_open_plan_only_v1",
        research_lead="Chase Lunsford / CaMaLabs",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        authorizes_paid_runtime=False,
        require_verified_active_plan="open",
        allow_simulators=False,
        N=15,public_base=2,phase_bits=4,
        phase_recycled_qubits=5,wide_qubits=8,
        shots_per_circuit=MAX_SHOTS,max_execution_time_seconds=MAX_RUNTIME_SEC,
        submission_performed=False,status="PREFLIGHT_PENDING",
        disclaimer="actual device experiment if submitted; toy N=15 classical factors trivial; a^3 no order shortening for order 4")
    save(out)
    token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
    instance=os.environ.get("IBM_QUANTUM_INSTANCE","").strip()
    # A local workstation may have a saved IBM account; a fresh GitHub
    # runner will not. In both cases, the ACTIVE service must still pass
    # strict open-only verification immediately before any Sampler.run.
    kwargs=dict(channel="ibm_quantum_platform",
                plans_preference=["open"],region="us-east")
    if token:
        kwargs["token"]=token
    if instance:
        kwargs["instance"]=instance
    try:
        service=QiskitRuntimeService(**kwargs)
    except Exception as exc:
        reason=("IBM_QUANTUM_API_KEY not available and no usable saved account in this execution environment"
                if not token else "IBM Quantum configured credential rejected")
        return blocked(out,reason+" ("+type(exc).__name__+").")
    try:
        # Guard the initial plan and confirm this is an actual free/open instance.
        assert_open_plan_submission(service)
        backend=shor.select_backend(service,8,None)
        if backend is None:
            return blocked(out,"No backend available for 8-qubit matched QPU.")
        if getattr(backend,"simulator",False):
            return blocked(out,"Selected backend is a simulator, never a real QPU.")
        if backend.num_qubits<8:
            return blocked(out,"The selected QPU lacks eight physical qubits.")
        if not backend.status().operational:
            return blocked(out,"Backend not operational.")
        instructions=set(getattr(backend,"supported_instructions",[]) or [])
        if not {"measure","reset"}.issubset(instructions):
            return blocked(out,"QPU lacks required mid-circuit measure/reset instructions.")
        proof=assert_open_plan_submission(service,backend)
        assert proof["open_plan_verified"] and str(proof["plan"]).lower()=="open"
        out["verified_plan"]="open"
        out["backend"]=backend.name
        out["backend_qubits"]=backend.num_qubits
        out["account_identifiers_redacted"]=True
    except Exception as exc:
        return blocked(out,"Open-Plan or operational-backend proof failed ("+type(exc).__name__+").")
    try:
        orig=[shor.build_recycled_shor15(4,shor.backend_has_measure2(backend)),
              shor.build_wide_shor15(4)]
        compiled=[shor.compile_circuit(qc,backend,optimization_level=2) for qc in orig]
        stats=[shor.circuit_stats(qc,isa,name)
               for qc,isa,name in zip(orig,compiled,("recycled","wide"))]
        out["transpiled_stats"]=stats
        for s in stats:
            operations=s["count_ops"]
            native_two=sum(v for k,v in operations.items() if k.lower() in ("cz","cx","ecr","rzz","iswap"))
            if s["depth"]>MAX_COMPILED_DEPTH or native_two>MAX_NATIVE_2Q:
                return blocked(out,f"Compiled circuit too large for frozen free-runtime guard: {s['kind']} depth={s['depth']} twoq={native_two}")
            if s["compiled_qubits"]>backend.num_qubits:
                return blocked(out,"Compiled circuit exceeds actual available device qubits.")
        print("REAL QPU preflight architecture/depth/native counts PASS",
              [(s["kind"],s["depth"],s["count_ops"]) for s in stats],flush=True)
        # The CRITICAL guard is deliberately called last, immediately before
        # Sampler.run, since backend discovery may change active instance.
        proof=assert_open_plan_submission(service,backend)
        assert proof["open_plan_verified"] and str(proof["plan"]).lower()=="open"
        out["final_open_plan_proof"]=True
        out["status"]="READY_FOR_OPEN_ONLY_SUBMISSION"
        save(out)
        sampler=SamplerV2(mode=backend,options={"max_execution_time":MAX_RUNTIME_SEC})
        job=sampler.run(compiled,shots=MAX_SHOTS)
        out.update(status="SUBMITTED_REAL_QPU",submission_performed=True,job_id=job.job_id())
        save(out)
        print("SUBMITTED ONE REAL IBM OPEN PLAN QPU JOB",job.job_id(),"backend",backend.name,flush=True)
        # Persist job receipt as soon as submitted. A queued/long-running job
        # is NOT reported as completed if result() is unavailable.
        try:
            pubs=job.result(timeout=420)
        except Exception as exc:
            out.update(status="SUBMITTED_PENDING_OR_RESULT_ERROR",
               result_unavailable_reason=type(exc).__name__)
            save(out)
            print("Real QPU submission preserved, result not yet verified.",type(exc).__name__,flush=True)
            return 0
        actual=[]
        for pub,kind in zip(pubs,("recycled","wide")):
            counts=pub.data.phase.get_counts()
            check=shor.analyze_counts(counts,4)
            actual.append(dict(architecture=kind,counts=counts,
               proper_factor_shot_fraction=check["factor_success_probability_per_shot"],
               factor_recovered=check["aggregate_factor_recovered"],
               factors=check["recovered_factor_counts"]))
        out.update(status="MEASURED_REAL_QPU",results=actual)
        save(out)
        print("REAL QPU HARDWARE RESULTS",json.dumps(actual),flush=True)
    except RuntimePlanGuardError as exc:
        return blocked(out,"Fail-closed Open Plan guard rejected submission ("+type(exc).__name__+").")
    except Exception as exc:
        if out.get("submission_performed"):
            out.update(status="SUBMITTED_RESULT_OR_API_ERROR",
                result_unavailable_reason=type(exc).__name__)
            save(out)
            print("JOB WAS SUBMITTED but result extraction failed:",type(exc).__name__,flush=True)
        else:
            return blocked(out,"Compile/preflight/submit failed with no confirmed QPU job ("+type(exc).__name__+").")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
