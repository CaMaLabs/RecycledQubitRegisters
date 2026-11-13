#!/usr/bin/env python3
"""Read-only local evidence inventory for Helios K001-K097.

No experiment execution, verification, package imports, git operations, file
rewrites in experiment folders, or network calls. Only metadata and bounded
result snippets are inspected. Writes ONE JSON inventory under requested path.
"""
import argparse,hashlib,json,re
from pathlib import Path
CAP=2_000_000
NAMES=("status","score","baseline_score","candidate_score","verified_score",
"best_score","verification_status","beats_baseline","winner","pass",
"full_passes","tested","total","cost","qubits","num_qubits","toffoli_count",
"toffoli_like","n_rot","rotations","x_tested","max_x","model_error")
def snapshot(path,root):
 st=path.stat()
 row={"path":str(path.relative_to(root)),"size":st.st_size}
 if st.st_size<=CAP and path.suffix==".json":
  try:
   d=json.loads(path.read_text())
   if isinstance(d,dict):
    row["json_top_keys"]=list(d)[:50]
    row["key_metrics"]={k:v for k,v in d.items() if k.lower() in NAMES
                       and isinstance(v,(int,float,bool,str,type(None)))}
    for k in ("result","summary","metrics","baseline","winner","verification"):
     x=d.get(k)
     if isinstance(x,dict):
      row[k+"_metrics"]={z:v for z,v in x.items() if z.lower() in NAMES
                         and isinstance(v,(int,float,bool,str,type(None)))}
   else:row["json_top_type"]=type(d).__name__
  except (OSError,UnicodeError,ValueError) as exc:row["read_error"]=str(exc)[:150]
 elif path.suffix in (".log",".txt",".jsonl"):
  if st.st_size<5_000_000:
   terms=("K0","RESULT","PASS","FAIL","score","winner","verifier","ERROR")
   try:
    with path.open(errors="replace") as f:
     hits=[s.strip()[:500] for s in f if any(t in s for t in terms)]
    row["tail_evidence_lines"]=hits[-12:]
   except OSError as exc:row["read_error"]=str(exc)[:150]
 return row
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",type=Path,default=Path("competition"))
 p.add_argument("--out",type=Path,default=Path("competition/K001_K097_LOCAL_INVENTORY.json"))
 p.add_argument("--max-files-per-run",type=int,default=120)
 p.add_argument("--max-depth",type=int,default=5)
 a=p.parse_args()
 if not a.root.is_dir():p.error("root missing")
 if a.max_files_per_run<1 or a.max_depth<1:p.error("bounds must be positive")
 runs={}
 for n in range(1,98):
  folders=[a.root/f"k{n:03d}",a.root/f"K{n:03d}"]
  found=[x for x in folders if x.is_dir()]
  if not found:continue
  files=[]
  for folder in found:
   for x in folder.rglob("*"):
    if not x.is_file() or x.is_symlink() or len(x.relative_to(folder).parts)>a.max_depth:continue
    if "/.git/" in str(x):continue
    files.append(x)
  files.sort(key=lambda x:(x.suffix not in (".json",".log",".txt",".jsonl"),x.stat().st_size,str(x)))
  items=[snapshot(x,a.root) for x in files[:a.max_files_per_run]]
  runs[f"K{n:03d}"]={"folders":[str(x) for x in found],"file_count":len(files),
    "file_count_inspected":len(items),"files":items}
 report={"status":"LOCAL_RECEIPT_INVENTORY_NOT_EXPERIMENT_RESULTS",
 "root":str(a.root),"runs_found":len(runs),
 "k_numbers_found":list(runs),
 "missing_k_numbers":[f"K{x:03d}" for x in range(1,98) if f"K{x:03d}" not in runs],
 "runs":runs,
 "limitations":["The absence of a local folder does not prove an experiment was never run.",
 "No circuit was executed or verified by this script.",
 "Large JSON files and logs are not fully parsed; log tail lines are contextual only.",
 "Output may include local paths or raw error text; inspect before publishing."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2,default=str)+"\n")
 print("EARLY_AUDIT_RESULT",json.dumps({"status":report["status"],
  "runs_found":report["runs_found"],"missing":len(report["missing_k_numbers"]),
  "output":str(a.out)}))
 print("EARLY_AUDIT_FOUND",",".join(report["k_numbers_found"]))
if __name__=="__main__":main()
