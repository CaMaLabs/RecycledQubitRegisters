#!/usr/bin/env python3
"""A31: reproducible cross-stage integration ledger, zero QPU.

Runs actual existing A24, A26, A27, A29, A30 Python programs without replacing
their algorithms. Optional A23 exact Quaspy bridge can be supplied explicitly
with --a23-command; the script never silently assumes it is installed.
Records different cohorts/units as incompatible, never sums fake speedups.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STAGES={
 "A24_public_first":"integrations/darkstar_hybrid/qrr_a24_n35_public_first_gate.py",
 "A26_exact_fourier":"hardware/qrr_a26_fourier_kernel_audit.py",
 "A27_reversible_fourier":"hardware/qrr_a27_reversible_fourier_comparison.py",
 "A29_residue_control":"hardware/qrr_a29_four_arm_residue_proxy.py",
 "A30_original_ptp_midpoint":"hardware/qrr_a30_original_ptp_source_adapter.py",
}
def run_process(label,argv,timeout,outdir):
    t0=time.perf_counter()
    try:
        proc=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,
                            timeout=timeout,check=False)
        stdout,stderr,rc=proc.stdout,proc.stderr,proc.returncode
        status="PASS" if rc==0 else "FAIL"
    except subprocess.TimeoutExpired as exc:
        stdout=(exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout,bytes) else (exc.stdout or "")
        stderr=(exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr,bytes) else (exc.stderr or "")
        rc=None
        status="TIMEOUT"
    (outdir/(label+".stdout.log")).write_text(stdout)
    (outdir/(label+".stderr.log")).write_text(stderr)
    payload=None
    if status=="PASS":
        try: payload=json.loads(stdout)
        except json.JSONDecodeError: status="INVALID_JSON"
    declared=payload.get("status") if isinstance(payload,dict) else None
    if status=="PASS" and (not declared or not declared.startswith("PASS")):
        status="UNEXPECTED_STATUS"
    return dict(stage=label,status=status,declared_status=declared,
                exit_code=rc,elapsed_seconds=round(time.perf_counter()-t0,6),
                command=argv,json_report=payload,
                stdout_log=str(outdir/(label+".stdout.log")),
                stderr_log=str(outdir/(label+".stderr.log")))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--outdir",type=Path,default=Path("results/a31_integration"))
    parser.add_argument("--timeout",type=int,default=120)
    parser.add_argument("--a23-command",default=None,
        help="Explicit standalone command for existing exact Quaspy bridge (optional)")
    args=parser.parse_args()
    if not 5 <= args.timeout <= 3600: parser.error("timeout must be 5..3600 seconds")
    out=args.outdir.resolve();out.mkdir(parents=True,exist_ok=True)
    records=[]
    for label,rel in STAGES.items():
        path=ROOT/rel
        if not path.is_file(): raise SystemExit("Required existing source missing: "+rel)
        records.append(run_process(label,[sys.executable,str(path)],args.timeout,out))
    if args.a23_command:
        records.append(run_process("A23_exact_quaspy",shlex.split(args.a23_command),
                                   args.timeout,out))
    else:
        records.append(dict(stage="A23_exact_quaspy",status="NOT_EXECUTED",
            reason="A23 remains independently verified from earlier user execution; supply explicit --a23-command to rerun same environment."))
    sources={rel:sha(ROOT/rel) for rel in STAGES.values()}
    reused={
        "ptp_factor_pair_and_kernel":"A30 directly imports simulation/ptp_hybrid/core.py and kernel.py",
        "fermat_midpoint":"A30 directly imports hardware/dark_star_ptp_shor_audit.py",
        "binary_fourier_kernel":"A26/A27/A30 exact small-cohort checks",
        "classical_first":"A24 public-only N35 wheel gate",
        "quaspy":"A23 verified separately; re-run only when supplied",
        "recycled_registers":"A21 prior independent evidence; not executed by this runner",
        "original_lwe_spectral_ntt":"LWE_GeometryLab experiments/ring_ntt_probe.py exists; ring-LWE error support model, NOT factoring pruning and not executed",
    }
    all_required_pass=all(r["status"]=="PASS" for r in records[:len(STAGES)])
    summary={
      "experiment":"A31_EXACT_SOURCE_MULTI_STAGE_LEDGER",
      "status":"PASS_COMPONENT_REPLAY_WITH_GAPS" if all_required_pass else "FAIL_COMPONENT_REPLAY",
      "qpu_jobs":0,"required_stage_passes":sum(r["status"]=="PASS" for r in records[:len(STAGES)]),
      "required_stage_count":len(STAGES),
      "integrated_end_to_end_factoring":False,
      "quaspy_same_cohort_live":bool(args.a23_command and records[-1]["status"]=="PASS"),
      "recycled_registers_same_circuit_live":False,
      "original_lwe_ntt_as_factoring_pruner":False,
      "quantum_speedup_measured":False,
      "source_sha256":sources,
      "reused_components":reused,
      "blocking_gaps":[
        "Different-stage arithmetic and factoring cohorts are not equivalent experiments.",
        "Original LWE NTT support/coherence methods are lattice-specific, not an RSA factoring oracle.",
        "A23 Quaspy bridge is ideal spectral distribution; no full compiled Shor gate-level circuit.",
        "Real recycled register reuse and modular exponentiation are not connected to these A30 tests.",
        "Gate and rotation count units differ; no common fault-tolerant resource denominator.",
        "Classical preprocessing and factoring baselines must include elapsed time and competent Brent rho."
      ],
      "records":records
    }
    (out/"a31_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k!="records"},indent=2))
    print("SAVED",out/"a31_summary.json")
    return 0 if all_required_pass else 1
if __name__=="__main__":
    raise SystemExit(main())
