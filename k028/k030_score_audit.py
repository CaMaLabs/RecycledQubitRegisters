#!/usr/bin/env python3
"""K030: official score audit + verified candidate resource decomposition.

Read-only. No changes to the scorer or competition files. Extracts scoring
implementation snippets, Kickmix resource methods and matched candidate scores.
Uses official verifier with valid shot batches, default max_x=64 to avoid large
compute. Emits JSON and a Markdown report in competition/k030/results.
"""
from __future__ import annotations
import ast
import inspect
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
K001=ROOT/"competition/k001/private/official/verifiers"
OUT=ROOT/"competition/k030/results"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0,str(K001))
import kickmix as km

SCORER=K001/"invsqrt/verify_submission_invsqrt.py"
REFERENCE=K001/"invsqrt/nr_reference_circuit.py"
RESOURCES=ROOT/"competition/k026/multimethod_overnight_campaign.py"
FILES={
    "control":ROOT/"competition/k029c/results/reference.kmb",
    "short_operand":ROOT/"competition/k029c/results/short_source.kmb",
    "wallace":ROOT/"competition/k028c/results/wallace_m.kmb",
    "controlled_add":ROOT/"competition/k028d/results/controlled_m.kmb",
    "complement_all":ROOT/"competition/k029a/results/qrr_complement_all.kmb",
    "square_even_odd":ROOT/"competition/k028e/results/square_even_odd.kmb",
}

def source_spans(path, keywords, radius=7, limit=35):
    lines=path.read_text().splitlines()
    hits=[]
    for i,line in enumerate(lines):
        if any(re.search(r"\b"+re.escape(k)+r"\b",line,re.I) for k in keywords):
            hits.append(i)
    blocks=[]
    for i in hits[:limit]:
        lo=max(0,i-radius);hi=min(len(lines),i+radius+1)
        blocks.append({"center":i+1,"text":"\n".join(f"{j+1:4}: {lines[j]}" for j in range(lo,hi))})
    return blocks

def methods(obj):
    return sorted(x for x in dir(obj) if not x.startswith("_") and
                  any(t in x.lower() for t in
                      ("resource","stat","count","cost","t_count","depth","qubit","volume","graph","gate")))

def resource_stats(circuit):
    # Use only source-established stats() where possible. Do not guess a
    # resource formula: property lists are for diagnostics, not scored claims.
    p=RESOURCES
    if p.exists():
        tree=ast.parse(p.read_text())
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name=="stats":
                # Extract exact K026 implementation with its own imports.
                module=ast.Module(body=[node],type_ignores=[])
                ns={"km":km}
                try:
                    exec(compile(module,str(p),"exec"),ns)
                    v=ns["stats"](circuit)
                    if isinstance(v,dict):
                        return {"source":"K026 stats()",**v}
                    return {"source":"K026 stats()","value":repr(v)}
                except Exception as e:
                    return {"stats_error":repr(e)}
    # Generic public attributes only, avoiding expensive/unknown calls.
    return {"error":"K026 stats() not available"}

def verify(path,max_x=64,seed=12345):
    verifier=SCORER
    batch=min(256,max_x)
    while max_x%batch:batch-=1
    cmd=[sys.executable,str(verifier),str(path),"--format","kmb",
         "--max-x",str(max_x),"--shots-per-x","1",
         "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
    began=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=K001,text=True,capture_output=True,timeout=300)
        try:j=json.loads(p.stdout)
        except ValueError:j={"status":"NON_JSON","stdout_tail":p.stdout[-800:]}
        return {"status":j.get("status"),"exit":p.returncode,
                "score":j.get("score"),"error_ratio":j.get("worst_error_over_tolerance"),
                "error":j.get("error"),"elapsed":round(time.monotonic()-began,3),
                "stderr_tail":p.stderr[-300:]}
    except Exception as e:
        return {"status":"EXCEPTION","error":repr(e)}

def main():
    print("K030 OFFICIAL SCORING SOURCE:",SCORER,flush=True)
    print("K030 CANDIDATE RESOURCE AUDIT",flush=True)
    report={
        "source_paths":{"scorer":str(SCORER),"reference":str(REFERENCE)},
        "scorer_source":source_spans(SCORER,["score","resource","volume","tcount","t_count","runtime","qubit","count"],5,50),
        "reference_source":source_spans(REFERENCE,["init_and","del_and","iadd","isub"],3,20),
        "kickmix_circuit_resource_methods":methods(km.Circuit),
        "kickmix_builder_resource_methods":methods(km.CircuitBuilder),
        "candidates":{},
    }
    # Detect where the verifier obtains the score, including imports.
    scorer=SCORER.read_text()
    report["scorer_import_lines"]=[line for line in scorer.splitlines()
        if line.startswith(("from ","import "))][:80]
    for name,path in FILES.items():
        if not path.exists():
            print("SKIP",name,"file absent",flush=True)
            continue
        print("AUDIT",name,flush=True)
        try:
            c=km.Circuit.from_file(str(path))
            stats=resource_stats(c)
        except Exception as e:stats={"error":repr(e)}
        official=verify(path)
        report["candidates"][name]={"path":str(path),"file_bytes":path.stat().st_size,
                                     "resource_stats":stats,"official":official}
        print(json.dumps({"name":name,**report["candidates"][name]},
                         sort_keys=True,default=str),flush=True)
    dest=OUT/"score_audit.json"
    dest.write_text(json.dumps(report,indent=2,default=str))
    md=["# K030 scorer audit (read-only)","",
        "The file contains excerpts from the locally installed official scorer.",
        "We do not alter the scorer or submit invalid candidates.","",
        "## Official-source score-related lines",""]
    for hit in report["scorer_source"]:
        md.extend(["```python",hit["text"],"```",""])
    md.extend(["## Available Kickmix resource methods","",
               "`"+", ".join(report["kickmix_circuit_resource_methods"])+"`","",
               "## Resource candidates","",
               "| Candidate | Score (max_x=64) | Status | File bytes |",
               "|---|---:|---|---:|"])
    for k,v in report["candidates"].items():
        sc=v["official"]["score"]
        md.append(f'| {k} | {sc if sc is not None else "N/A"} | {v["official"]["status"]} | {v["file_bytes"]} |')
    (OUT/"score_audit.md").write_text("\n".join(md)+"\n")
    print("SAVED",dest,OUT/"score_audit.md",flush=True)

if __name__=="__main__":main()
