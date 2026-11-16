#!/usr/bin/env python3
"""K174 read-only baseline compatibility audit; does NOT modify the KMX."""
import argparse, hashlib, json, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"k171"))
import k171_shared_monomial as k171

PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=pathlib.Path,default=pathlib.Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("competition/k174/results/baseline_audit.json"))
 a=p.parse_args()
 if not a.baseline.is_file():raise SystemExit("MISSING_BASELINE "+str(a.baseline))
 data=a.baseline.read_bytes()
 sha=hashlib.sha256(data).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 gates,_=k171.build()
 k171.verify(gates,1000)
 sample=data[:512]
 report={"baseline":str(a.baseline),"sha256":sha,"pinned":True,"size_bytes":len(data),
         "prefix_hex":sample[:128].hex(),"prefix_utf8":sample.decode("utf-8","replace")[:512],
         "k171_gates":k171.count(gates),"k171_wires":25,
         "k171_lookup_verified":True,"substitution_compatible":None,
         "integrated":False,"official_score_verified":False,
         "next":"Identify KMX parser and precise lookup boundaries; require semantic equivalence before patching."}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K174_AUDIT",json.dumps(report,sort_keys=True))
 print("K174_WRITTEN",a.out)
if __name__=="__main__":main()
