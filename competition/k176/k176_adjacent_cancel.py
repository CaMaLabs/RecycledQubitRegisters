#!/usr/bin/env python3
"""K176 conservative full-Helios adjacent inverse-pair cancellation.

Only identical adjacent unconditional X/Z/CX/CZ/CCX/CCZ/SWAP/CSWAP
instructions are canceled. All other instructions are opaque barriers,
including measurement, classical conditions, register operations and R.
Writes a new candidate; never overwrites pinned baseline.
"""
import argparse, collections, hashlib, json, pathlib
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
INV={"X","Z","CX","CZ","CCX","CCZ","SWAP","CSWAP"}
def eligible(line):
 s=line.strip().split()
 if not s or s[0] not in INV:return None
 n={"X":2,"Z":2,"CX":3,"CZ":3,"CCX":4,"CCZ":4,"SWAP":3,"CSWAP":4}[s[0]]
 if len(s)!=n or any(not x.startswith("q") or not x[1:].isdigit() for x in s[1:]):return None
 if len(set(s[1:]))!=len(s)-1:return None
 return tuple(s)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=pathlib.Path,default=pathlib.Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--candidate",type=pathlib.Path,default=pathlib.Path("competition/k176/results/helios_adjacent_cancel.kmx"))
 p.add_argument("--report",type=pathlib.Path,default=pathlib.Path("competition/k176/results/adjacent_cancel.json"))
 a=p.parse_args()
 raw=a.baseline.read_bytes()
 sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 lines=raw.splitlines(keepends=True)
 # Keep exact original bytes for every surviving line; no reserialization.
 stack=[];removed=collections.Counter();pairs=[]
 for i,line in enumerate(lines):
  s=line.decode("utf-8").strip()
  key=eligible(s)
  if key and stack and stack[-1][1]==key:
   prev=stack.pop()
   removed[key[0]]+=2
   pairs.append([prev[2]+1,i+1,key[0]])
  else:
   # A non-eligible instruction blocks cancellation. Eligible instructions
   # may only cancel after earlier pairs have been removed.
   stack.append((line,key,i))
 candidate=b"".join(item[0] for item in stack)
 # Independent replay of deletion witness, including exact original pairs.
 check=list(lines)
 for left,right,op in reversed(pairs):
  # Witness line numbers are original, not transformed; rely on stack logic
  # and byte-exact candidate reconstruction rather than index deletion.
  assert eligible(lines[left-1].decode("utf-8"))==eligible(lines[right-1].decode("utf-8"))
 assert candidate==raw if not pairs else candidate!=raw
 counts=lambda data:dict(collections.Counter(line.split(None,1)[0].decode("utf-8") for line in data.splitlines() if line.strip()))
 before=counts(raw);after=counts(candidate)
 for op,n in removed.items():assert before[op]-after[op]==n
 for op in set(before)|set(after):
  if op not in removed:assert before.get(op,0)==after.get(op,0)
 a.candidate.parent.mkdir(parents=True,exist_ok=True)
 a.candidate.write_bytes(candidate)
 report={"baseline_sha256":sha,"candidate_sha256":hashlib.sha256(candidate).hexdigest(),
         "baseline_lines":len(lines),"candidate_lines":len(candidate.splitlines()),
         "removed_instructions":sum(removed.values()),"removed_by_opcode":dict(removed),
         "pair_witness_first_30":pairs[:30],
         "exact_local_rewrite":"Adjacent identical unconditional involutions only; opaque instructions are barriers",
         "candidate_path":str(a.candidate),"candidate_bytes":len(candidate),
         "official_verifier_pass":None,"official_score":None,
         "score_claim":"NONE; run existing official verifier before considering submission"}
 a.report.parent.mkdir(parents=True,exist_ok=True)
 a.report.write_text(json.dumps(report,indent=2)+"\n")
 print("K176_RESULT",json.dumps(report,sort_keys=True),flush=True)
 print("K176_WRITTEN",a.report,flush=True)
if __name__=="__main__":main()
