#!/usr/bin/env python3
"""K002: read-only local inspection of official verifier interfaces.

Does not load the 886-MB DQI circuit, execute downloaded code, publish
competition source, or submit to Kaggle. It inventories command-line arguments,
entry points, imports, and likely kickmix APIs using Python AST parsing.
"""
import ast,json,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OFFICIAL=ROOT/"../k001/private/official"
VERIFIERS=OFFICIAL/"verifiers"
OUT=ROOT/"k002_interface_report.json"
SOURCES={
 "invsqrt_verifier":"invsqrt/verify_submission_invsqrt.py",
 "invsqrt_reference":"invsqrt/nr_reference_circuit.py",
 "dqi_verifier":"dqi/verify_submission_dqi.py",
 "dqi_reference":"dqi/dqi_reference_circuit.py",
 "chem_verifier":"dfthcsos/verify.py",
 "chem_circuits":"dfthcsos/scoreinfra/circuits.py",
 "chem_costs":"dfthcsos/scoreinfra/costs_prepare.py",
 "chem_example":"dfthcsos/example_submission/angle_k_reference_circuit.py",
}
def name(node):
 if isinstance(node,ast.Name):return node.id
 if isinstance(node,ast.Attribute):return name(node.value)+"."+node.attr
 return None
def literal(node):
 try:
  val=ast.literal_eval(node)
  if isinstance(val,(str,int,float,bool,type(None))):
   return val if not isinstance(val,str) or len(val)<250 else val[:250]
 except (ValueError,TypeError,RecursionError):pass
 return None
def inspect(path):
 tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
 imports=set();functions=[];classes=[];cli=[];callnames=set()
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.update(alias.name for alias in node.names)
  elif isinstance(node,ast.ImportFrom):
   imports.add((node.module or "")+"."+",".join(alias.name for alias in node.names))
  elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
   if isinstance(node,ast.FunctionDef):
    args=[arg.arg for arg in node.args.args]
    if not node.name.startswith("_"):
     functions.append({"name":node.name,"args":args[:18],"line":node.lineno})
  elif isinstance(node,ast.ClassDef):classes.append(node.name)
  elif isinstance(node,ast.Call):
   c=name(node.func)
   if c:callnames.add(c)
   if c and c.endswith("add_argument"):
    vals=[literal(arg) for arg in node.args[:2]]
    opts=[{"key":kw.arg,"value":literal(kw.value)} for kw in node.keywords if kw.arg in ("required","default","type","action","nargs","help")]
    cli.append({"args":vals,"options":opts})
 return {"bytes":path.stat().st_size,"imports":sorted(imports)[:60],
  "top_level_public_functions":functions[:80],"classes":classes[:50],
  "argument_definitions":cli[:100],
  "relevant_calls":sorted(n for n in callnames if re.search(r"kickmix|load|dump|sav|read|writ|verif|cost|score|check|circuit|npz|qasm|submit",n,re.I))[:100]}
def main():
 if not VERIFIERS.exists():raise SystemExit("K001 official verifier files not found; run bootstrap first")
 d={"status":"K002_LOCAL_INTERFACE_INSPECTION","official_sources_executed":False,
   "competition_submission_attempted":False,"source_content_redistributed":False,
   "verifiers":{},"docs":{},"samples":{}}
 for label,relative in SOURCES.items():
  path=VERIFIERS/relative
  try:d["verifiers"][label]=inspect(path)
  except Exception as exc:d["verifiers"][label]={"error":f"{type(exc).__name__}: {exc}"}
 for label,rel in {"chem_scoring":"verifiers/dfthcsos/SCORING_README.md"}.items():
  p=OFFICIAL/rel
  if p.is_file():
   contents=p.read_text(encoding="utf-8",errors="replace")
   # Report section titles only, not official document passages.
   d["docs"][label]={"size":p.stat().st_size,"headings":[x.strip()[:180] for x in contents.splitlines() if x.lstrip().startswith("#")][:60]}
 for label,rel in {"invsqrt":"sample_submission/invsqrt.kmb","dqi":"sample_submission/dqi.kmb",
                   "chem_npz":"sample_submission/dfthcsos/submission.npz"}.items():
  p=OFFICIAL/rel
  if p.exists():d["samples"][label]={"bytes":p.stat().st_size}
 OUT.parent.mkdir(parents=True,exist_ok=True)
 OUT.write_text(json.dumps(d,indent=2)+"\n")
 print("K002 STATUS",d["status"],flush=True)
 print("K002 REPORT",OUT,flush=True)
 for label,row in d["verifiers"].items():
  print("K002",label,
   "functions",[(f["name"],f["args"]) for f in row.get("top_level_public_functions",[])[:12]],
   "CLI",[x["args"] for x in row.get("argument_definitions",[])[:25]],
   "relevant_calls",row.get("relevant_calls",[])[:30],flush=True)
 print("K002 NOTE: inspect the saved report for exact APIs before writing a candidate.",flush=True)
if __name__=="__main__":main()
