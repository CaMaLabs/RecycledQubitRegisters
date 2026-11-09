#!/usr/bin/env python3
"""K068: exact shared-control Toffoli factoring; public Helios is benchmark only.
CCX(a,b,t) CCX(a,c,t) == CX(b,c) CCX(a,c,t) CX(b,c).
The intervening gates, if any, must be unconditional, well-formed and
disjoint from all four qubits. Full-domain verification is mandatory for wins.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
PAT=re.compile(r"^CCX\s+q(\d+)\s+q(\d+)\s+q(\d+)\s*$")
Q=re.compile(r"\bq(\d+)\b")
ARITY={"X":1,"Y":1,"Z":1,"H":1,"S":1,"T":1,"CX":2,"CZ":2,"SWAP":2,
       "CCX":3,"CCZ":3,"CSWAP":3,"Z_POW":1}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(s):
 s=s.strip()
 if not s or " if " in s:return None
 op=s.split()[0]
 if op not in ARITY:return None
 q=tuple(int(n) for n in Q.findall(s))
 if len(q)!=ARITY[op] or len(set(q))!=len(q):return None
 return op,q
def relation(one,two):
 a=PAT.fullmatch(one.strip());b=PAT.fullmatch(two.strip())
 if not a or not b:return None
 x,y,t=map(int,a.groups());z,w,u=map(int,b.groups())
 if t!=u or len({x,y,t})!=3 or len({z,w,u})!=3:return None
 common={x,y}&{z,w}
 if len(common)!=1:return None
 common=next(iter(common));b=next(iter({x,y}-{common}));c=next(iter({z,w}-{common}))
 return (common,b,c,t) if len({common,b,c,t})==4 else None
def factor(lines,limit):
 parsed=[parse(s) for s in lines]
 matches=[];used=set()
 for i,item in enumerate(parsed):
  if i in used or item is None or item[0]!="CCX":continue
  for j in range(i+1,min(len(lines),i+limit+1)):
   if j in used or parsed[j] is None:break
   rel=relation(lines[i],lines[j]) if parsed[j][0]=="CCX" else None
   if rel and all(parsed[k] is not None and not set(rel).intersection(parsed[k][1])
                  for k in range(i+1,j)):
    matches.append((i,j,rel));used.update((i,j));break
   if set(item[1]).intersection(parsed[j][1]):break
 if not matches:return lines,[]
 updates={};deleted=set()
 for i,j,(common,b,c,t) in matches:
  updates[i]=[f"CX q{b} q{c}\n",f"CCX q{common} q{c} q{t}\n",f"CX q{b} q{c}\n"]
  deleted.add(j)
 out=[]
 for i,s in enumerate(lines):
  if i in deleted:continue
  out.extend(updates[i] if i in updates else [s])
 return out,matches
def exhaustive_test():
 def cx(v,a,t):return v^(((v>>a)&1)<<t)
 def ccx(v,a,b,t):return v^((((v>>a)&1)*((v>>b)&1))<<t)
 for a,b,c,t in ((0,1,2,3),(2,0,3,1),(3,2,1,0)):
  for v in range(16):
   direct=ccx(ccx(v,a,b,t),a,c,t)
   folded=cx(ccx(cx(v,b,c),a,c,t),b,c)
   assert direct==folded,(a,b,c,t,v)
 assert relation("CCX q0 q1 q3","CCX q0 q2 q3")==(0,1,2,3)
 sample=["CCX q0 q1 q3\n","Z q7\n","CCX q0 q2 q3\n"]
 out,found=factor(sample,10)
 assert len(found)==1 and sum(s.startswith("CCX") for s in out)==1
 # A gate touching second-only control is NOT movable through replacement.
 sample=["CCX q0 q1 q3\n","CX q5 q2\n","CCX q0 q2 q3\n"]
 out,found=factor(sample,10)
 assert not found and out==sample
 print("K068_SELFTEST PASS 48 basis cases + commutation barriers",flush=True)
def verify(path,full,timeout):
 p=ROOT/"competition/k031/k031_full_domain_repair.py"
 s=importlib.util.spec_from_file_location("k031_k068",p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 jobs=[("prefix",64,12345)]
 if full:jobs += [("full_12345",m.FULL_X,12345),("full_23456",m.FULL_X,23456)]
 d={}
 for label,n,seed in jobs:
  d[label]=m.verify(path,n,seed,timeout)
  if d[label].get("status")!="PASS" or d[label].get("exit_code")!=0:break
 return d
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",action="append",type=Path)
 p.add_argument("--out",type=Path,default=ROOT/"competition/k068/results")
 p.add_argument("--max-distance",type=int,default=96)
 p.add_argument("--full",action="store_true")
 p.add_argument("--timeout",type=int,default=600)
 p.add_argument("--self-test",action="store_true")
 a=p.parse_args()
 if a.self_test:exhaustive_test();return
 a.out.mkdir(parents=True,exist_ok=True)
 sources=a.source or [ROOT/"competition/k059/results"/(x+".kmx") for x in
                      ("helios_public","k040_ours","k056_bounded_ours")]
 results=[]
 for source in sources:
  if not source.is_file():
   print("K068_MISSING",source,flush=True);continue
  orig=source.read_text().splitlines(keepends=True)
  cand=orig;matches=[]
  for step in range(5):
   cand,found=factor(cand,a.max_distance)
   if not found:break
   matches.extend((step,i,j,rel) for i,j,rel in found)
  result={"source":str(source),"source_sha256":sha(source),
          "attribution":"third-party Helios" if "helios" in source.name else "CaMaLabs",
          "matched_pairs":len(matches),"CCX_saved":len(matches),
          "lines_before":len(orig),"lines_after":len(cand),
          "examples":matches[:10]}
  print("K068_SCAN",json.dumps(result,sort_keys=True),flush=True)
  if not matches:result["status"]="NO_MATCHES"
  else:
   try:
    import kickmix as km
    text=a.out/(source.stem+"_factored.kmx");text.write_text("".join(cand))
    circ=km.Circuit.from_file(str(text),format="kmx")
    target=text.with_suffix(".kmb");circ.to_file(str(target),format="kmb")
    result["candidate_sha256"]=sha(target)
    result["num_qubits"]=circ.num_qubits
    result["official"]=verify(target,a.full,a.timeout)
    good=all(r.get("status")=="PASS" and r.get("exit_code")==0
             for r in result["official"].values())
    result["status"]="PASS_FULL" if good and a.full and len(result["official"])==3 else (
        "PASS_PREFIX_ONLY" if good else "FAIL")
   except Exception as e:result["status"]="ERROR";result["error"]=repr(e)
  results.append(result)
  print("K068_RESULT",json.dumps({"source":result["source"],"status":result["status"],
    "CCX_saved":result["CCX_saved"],"error":result.get("error")},sort_keys=True),flush=True)
 (a.out/"results.json").write_text(json.dumps({"results":results},indent=2,default=str))
 print("K068_SAVED",a.out/"results.json",flush=True)
if __name__=="__main__":main()
