#!/usr/bin/env python3
"""K048: reproduce a PUBLIC independent invsqrt circuit with official verifier.

Does not copy or redistribute the reference kit or external circuits into Git.
Attribution: Agniv Banerjee, public dataset:
https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits
File: circuits/invsqrt/af4698478fba.kmb
The source is someone else's published work, NOT a CaMaLabs improvement.

Use --source /path/to/public/invsqrt.kmb after downloading with Kaggle.
Reports SHA, prefix, two-seed full domain, ratio vs frozen K040, and
provenance. Does not promote failures or assume author's score applies to
the local verifier salt. One deterministic local validation workflow.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sp=importlib.util.spec_from_file_location("k031_k048",ROOT/"competition/k031/k031_full_domain_repair.py")
k031=importlib.util.module_from_spec(sp);sp.loader.exec_module(k031)
EXPECTED_PREFIX="af4698478fba"
DATASET="manwithacat/vqcc-apache-public-circuits"
AUTHOR="Agniv Banerjee"
FROZEN_SCORE=1803994.6591350352

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True,
        help="Local copy of openly published invsqrt .kmb; NEVER commit to git")
    ap.add_argument("--out",type=Path,default=ROOT/"competition/k048/results")
    ap.add_argument("--timeout",type=int,default=300)
    ap.add_argument("--prefix",type=int,default=64)
    ap.add_argument("--full",action="store_true",
        help="Run both official full-domain seeds after 64-input PASS")
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if not args.source.is_file():
        raise SystemExit("Missing public source file: "+str(args.source))
    if args.source.suffix.lower() not in (".kmb",".kmx"):
        raise SystemExit("Expected .kmb/.kmx source")
    sha=hashlib.sha256(args.source.read_bytes()).hexdigest()
    # Public ledger names files by the first 12 SHA bytes.
    pinned=sha.startswith(EXPECTED_PREFIX)
    report={"published_author":AUTHOR,"public_dataset":DATASET,
        "public_file":"circuits/invsqrt/af4698478fba.kmb",
        "source":str(args.source.resolve()),"source_sha256":sha,
        "matches_published_hash_prefix":pinned,"bytes":args.source.stat().st_size,
        "local_control_full_score":FROZEN_SCORE}
    if not pinned:
        report["status"]="HASH_MISMATCH"
        (args.out/"result.json").write_text(json.dumps(report,indent=2))
        print("K048_HASH_MISMATCH",json.dumps(report,sort_keys=True),flush=True)
        return
    screen=k031.verify(args.source,args.prefix,12345,args.timeout)
    report["prefix"]=screen
    print("K048_PREFIX",json.dumps({"status":screen.get("status"),
        "score":screen.get("score"),"qubits":screen.get("num_qubits"),
        "toffolis":screen.get("toffoli_count")},sort_keys=True),flush=True)
    good=screen.get("status")=="PASS" and screen.get("exit_code")==0
    if good and args.full:
        for seed in (12345,23456):
            full=k031.verify(args.source,k031.FULL_X,seed,args.timeout)
            report[f"full_seed_{seed}"]=full
            print("K048_FULL",json.dumps({"seed":seed,
                "status":full.get("status"),"score":full.get("score"),
                "verified_shots":full.get("verified_shots"),
                "worst_error_over_tolerance":full.get("worst_error_over_tolerance")
            },sort_keys=True),flush=True)
            if full.get("status")!="PASS" or full.get("exit_code")!=0:break
    valid=all(report.get(f"full_seed_{s}",{}).get("status")=="PASS" and
              report.get(f"full_seed_{s}",{}).get("exit_code")==0
              for s in (12345,23456))
    report["status"]="PASS_FULL_PUBLIC_THIRD_PARTY" if valid else (
        "PASS_PREFIX_ONLY" if good else "FAIL_PREFIX")
    if valid:
        score=report["full_seed_12345"]["score"]
        report["local_full_score"]=score
        report["ratio_k040_over_public"]=FROZEN_SCORE/score
        report["qubits"]=report["full_seed_12345"].get("num_qubits")
    (args.out/"result.json").write_text(json.dumps(report,indent=2))
    print("K048_RESULT",json.dumps({"status":report["status"],
        "score":report.get("local_full_score"),
        "improvement_factor":report.get("ratio_k040_over_public"),
        "qubits":report.get("qubits"),
        "sha256":sha},sort_keys=True),flush=True)
    print("SAVED",args.out/"result.json",flush=True)
if __name__=="__main__":main()
