#!/usr/bin/env python3
"""K058: inspect public heliosli/qcc-circuits-live circuit dataset."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[2]
DATASET="heliosli/qcc-circuits-live"
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()
def verifier(p,full,timeout):
 ref=ROOT/"competition/k031/k031_full_domain_repair.py"
 if not ref.exists():return {"status":"MISSING_VERIFIER"}
 s=importlib.util.spec_from_file_location("k031_k058",ref)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 results={}
 for label,maxx,seed in [("prefix",64,12345)]+([("full1",m.FULL_X,12345),("full2",m.FULL_X,23456)] if full else []):
  r=m.verify(p,maxx,seed,timeout);results[label]=r
  if r.get("status")!="PASS" or r.get("exit_code")!=0:break
 return results
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--out",type=Path,default=ROOT/"competition/k058/results")
 ap.add_argument("--existing",action="store_true")
 ap.add_argument("--full",action="store_true")
 ap.add_argument("--timeout",type=int,default=600)
 args=ap.parse_args()
 args.out.mkdir(parents=True,exist_ok=True)
 data=args.out/"dataset";data.mkdir(parents=True,exist_ok=True)
 if not args.existing:
  cmd=["kaggle","datasets","download","-d",DATASET,"-p",str(data),"--unzip"]
  print("K058_COMMAND",json.dumps(cmd),flush=True)
  r=subprocess.run(cmd,capture_output=True,text=True)
  print("K058_FETCH",json.dumps({"exit_code":r.returncode,"stdout":r.stdout[-1200:],"stderr":r.stderr[-1200:]}),flush=True)
  if r.returncode:raise SystemExit("Dataset download failed")
 items=[p for p in sorted(data.rglob("*")) if p.is_file()]
 circuits=[p for p in items if p.suffix.lower() in (".kmb",".kmx")]
 archives=[]
 for p in items:
  if p.suffix.lower()!=".zip":continue
  row={"path":str(p.relative_to(data)),"sha256":digest(p)}
  try:
   with zipfile.ZipFile(p) as z:
    row["members"]=[{"name":m.filename,"bytes":m.file_size} for m in z.infolist() if not m.is_dir()]
  except Exception as e:row["error"]=repr(e)
  archives.append(row)
 checks=[]
 for p in circuits:
  if p.name.lower()=="invsqrt.kmb":
   result={"path":str(p.relative_to(data)),"sha256":digest(p),"verification":verifier(p,args.full,args.timeout)}
   checks.append(result);print("K058_VERIFY",json.dumps(result),flush=True)
 audit={"dataset":DATASET,"author":"heliosli, plus respective circuit authors","files":[{"name":str(p.relative_to(data)),"bytes":p.stat().st_size,"sha256":digest(p)} for p in items],"archives":archives,"verifications":checks}
 (args.out/"audit.json").write_text(json.dumps(audit,indent=2))
 print("K058_RESULT",json.dumps({"files":len(items),"direct_circuits":len(circuits),"archives":len(archives),"verified":len(checks),"sample":[str(p.relative_to(data)) for p in circuits[:20]]}),flush=True)
 print("SAVED",args.out/"audit.json",flush=True)
if __name__=="__main__":main()
