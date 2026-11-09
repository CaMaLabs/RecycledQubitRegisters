#!/usr/bin/env python3
"""K057 — fetch public Helios Kaggle kernel artifacts and independently audit.

Source: https://www.kaggle.com/code/heliosli/the-dataset-is-public-now-enjoy
Public notebook; THIRD-PARTY circuits. Do NOT claim as own solutions.
The local original invsqrt verifier is used only for a standalone invsqrt
circuit extracted from the notebook's submission zip.

Run --fetch to download notebook source + output using installed Kaggle CLI
(authentication needed). Alternatively --input-dir points to previously
downloaded outputs or --zip to a local submission zip.

No inferred scoring from KMB size or compression; score uses gate/qubit
resources. SHA256 is recorded for all files and extracted circuit members.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,subprocess,sys,zipfile
from pathlib import Path
KERNEL="heliosli/the-dataset-is-public-now-enjoy"
ROOT=Path(__file__).resolve().parents[2]
def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def sha_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for buf in iter(lambda:f.read(1024*1024),b""):h.update(buf)
    return h.hexdigest()
def run(cmd):
    print("K057_COMMAND",json.dumps(cmd),flush=True)
    proc=subprocess.run(cmd,capture_output=True,text=True)
    print("K057_FETCH",json.dumps({
        "exit_code":proc.returncode,"stdout":proc.stdout[-1500:],
        "stderr":proc.stderr[-1500:]}),flush=True)
    if proc.returncode:raise RuntimeError("Kaggle command failed; check credentials and kernel availability")
def notebook_facts(path):
    j=json.loads(path.read_text())
    sources=[]
    for c in j.get("cells",[]):
        source=c.get("source",[])
        if isinstance(source,list):source="".join(source)
        for line in source.splitlines():
            if any(word in line.lower() for word in
                   ("kaggle.com/code/","kaggle.com/datasets/","apache-2.0",
                    "conditional uncompute","invsqrt","sha256")):
                sources.append(line[:300])
                if len(sources)>=35:break
        if len(sources)>=35:break
    return {"notebook":str(path),"headlines":sources}
def audit_zip(path,extract_dir):
    files=[]
    extracted=[]
    with zipfile.ZipFile(path) as z:
        for m in z.infolist():
            if m.is_dir():continue
            # Reject archive traversal and weird absolute member paths.
            name=m.filename
            pp=Path(name)
            if pp.is_absolute() or ".." in pp.parts:raise ValueError("Unsafe ZIP path "+name)
            data=z.read(m)
            files.append({"name":name,"bytes":len(data),
                          "sha256":sha_bytes(data)})
            if pp.name=="invsqrt.kmb" or pp.name=="invsqrt.kmx":
                output=extract_dir/pp.name
                output.parent.mkdir(parents=True,exist_ok=True)
                output.write_bytes(data)
                extracted.append(output)
    return files,extracted
def verify_one(path,timeout,full):
    modpath=ROOT/"competition/k031/k031_full_domain_repair.py"
    if not modpath.is_file():return {"status":"NO_LOCAL_VERIFIER"}
    spec=importlib.util.spec_from_file_location("k031_k057",modpath)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    # Existing K031 verify() uses --format kmb; only verify kmb files.
    if path.suffix!=".kmb":return {"status":"SKIP_NON_KMB","path":str(path)}
    checks={}
    prefix=mod.verify(path,64,12345,timeout)
    checks["prefix"]=prefix
    if prefix.get("status")=="PASS" and prefix.get("exit_code")==0 and full:
        a=mod.verify(path,mod.FULL_X,12345,timeout)
        checks["full_seed_12345"]=a
        if a.get("status")=="PASS" and a.get("exit_code")==0:
            checks["full_seed_23456"]=mod.verify(path,mod.FULL_X,23456,timeout)
    good=(all(checks.get(k,{}).get("status")=="PASS" for k in
              ("full_seed_12345","full_seed_23456"))
          and all(checks.get(k,{}).get("exit_code")==0 for k in
              ("full_seed_12345","full_seed_23456")))
    return {"status":"PASS_FULL_PUBLIC_THIRD_PARTY" if good else
            "PREFIX_ONLY_OR_FAIL","checks":checks}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,default=ROOT/"competition/k057/results")
    ap.add_argument("--fetch",action="store_true")
    ap.add_argument("--input-dir",type=Path)
    ap.add_argument("--zip",type=Path)
    ap.add_argument("--full",action="store_true")
    ap.add_argument("--timeout",type=int,default=300)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    download=a.out/"helios_kernel"
    if a.fetch:
        download.mkdir(exist_ok=True)
        run(["kaggle","kernels","pull",KERNEL,"-p",str(download),"--metadata"])
        run(["kaggle","kernels","output",KERNEL,"-p",str(download),"--force"])
    scan=a.input_dir or download
    if not scan.is_dir() and a.zip is None:
        raise SystemExit("Provide --fetch, --input-dir, or --zip")
    artifacts=[]
    if scan.is_dir():
        for p in sorted(scan.rglob("*")):
            if p.is_file():
                artifacts.append({"path":str(p),"size":p.stat().st_size,
                                  "sha256":sha_file(p)})
    zips=[a.zip] if a.zip else (
        sorted(scan.rglob("*.zip")) if scan.is_dir() else [])
    notebooks=[]
    for f in (sorted(scan.rglob("*.ipynb")) if scan.is_dir() else []):
        try:notebooks.append(notebook_facts(f))
        except Exception as exc:
            notebooks.append({"path":str(f),"error":repr(exc)})
    archives=[]
    for file in zips:
        if not file.is_file():continue
        row={"path":str(file),"sha256":sha_file(file)}
        try:
            members,invsqrt=audit_zip(file,a.out/"extracted")
            row["members"]=members
            row["invsqrt_verifications"]=[
                {"file":str(p),"sha256":sha_file(p),
                 "verification":verify_one(p,a.timeout,a.full)}
                for p in invsqrt]
        except Exception as exc:row["error"]=repr(exc)
        archives.append(row)
        print("K057_ARCHIVE",json.dumps({
            "path":row["path"],"members":len(row.get("members",[])),
            "invsqrt":row.get("invsqrt_verifications"),
            "error":row.get("error")},sort_keys=True),flush=True)
    report={"source_kernel":KERNEL,
            "attribution":"heliosli and individually credited circuit authors; not CaMaLabs original work",
            "license_note":"Check source-specific licenses and circuit notices before reuse",
            "artifacts":artifacts,"notebooks":notebooks,"archives":archives,
            "note":"Physical circuit score is not determined by kmb byte length or ZIP compression."}
    (a.out/"audit.json").write_text(json.dumps(report,indent=2,default=str))
    print("K057_RESULT",json.dumps({
        "kernel":KERNEL,"artifacts":len(artifacts),"notebooks":len(notebooks),
        "archives":len(archives),
        "invsqrt_found":sum(len(x.get("invsqrt_verifications",[])) for x in archives)},sort_keys=True),flush=True)
    print("SAVED",a.out/"audit.json",flush=True)
if __name__=="__main__":main()
