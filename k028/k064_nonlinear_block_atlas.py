#!/usr/bin/env python3
"""K064: find expensive routing/nonlinear blocks in the verified Helios circuit.

Read-only investigation. Third-party reference is never modified.
Analyzes:
 - CSWAP control / target pair repetition and adjacent/nearby constructions
 - CCX, CCZ and CSWAP concentrations in windows
 - conditional-vs-quantum controls
 - runs of repeated CSWAP control (conditional permutation candidates)
 - detailed excerpts around representative expensive blocks
The analysis does not assert an exact algorithm from local gate motifs.
"""
from __future__ import annotations
import argparse, collections, json, re, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q = re.compile(r"\bq(\d+)\b")
BIT = re.compile(r"\bb(\d+)\b")
COST = {"CCX", "CCZ", "CSWAP"}

def load(path):
    out=[]
    for lineno, s in enumerate(path.read_text(errors="replace").splitlines(),1):
        v=s.strip()
        if not v or v.startswith("#"): continue
        op=v.split()[0].upper()
        out.append({"line":lineno,"op":op,"text":v,
                    "q":tuple(int(x) for x in Q.findall(v)),
                    "b":tuple(int(x) for x in BIT.findall(v)),
                    "conditional":" if b" in v})
    return out

def sample_region(items, start, stop, max_lines=60):
    segment=items[max(0,start):min(len(items),stop)]
    if len(segment)>max_lines:
        cut=max_lines//2
        segment=segment[:cut]+[{"line":0,"text":"... omitted ..."}]+segment[-cut:]
    return [f"{x['line']}: {x['text']}" for x in segment]

def investigate(items, width, window, top, excerpt):
    n=len(items)
    stats=collections.Counter(v["op"] for v in items)
    cswaps=[(i,v) for i,v in enumerate(items) if v["op"]=="CSWAP" and len(v["q"])==3]
    controls=collections.Counter(v["q"][0] for _,v in cswaps)
    targetpairs=collections.Counter(tuple(sorted(v["q"][1:])) for _,v in cswaps)
    bycontrol=collections.defaultdict(list)
    for i,v in cswaps:bycontrol[v["q"][0]].append((i,v))
    runs=[]
    # consecutive CSWAPs with same quantum control; no intervening ops
    i=0
    while i<n:
        if items[i]["op"]!="CSWAP" or len(items[i]["q"])!=3:
            i+=1;continue
        ctl=items[i]["q"][0]
        j=i+1
        while j<n and items[j]["op"]=="CSWAP" and len(items[j]["q"])==3 and items[j]["q"][0]==ctl:
            j+=1
        if j-i>=2:
            runs.append({"control":ctl,"count":j-i,
                         "start_line":items[i]["line"],"end_line":items[j-1]["line"],
                         "pairs":[list(t["q"][1:]) for t in items[i:j]],
                         "excerpt":sample_region(items,i-4,j+4,excerpt)})
        i=j
    runs.sort(key=lambda v:v["count"],reverse=True)
    nearby=[]
    for ctl,instances in bycontrol.items():
        if len(instances)<2:continue
        for (a,va),(b,vb) in zip(instances,instances[1:]):
            if b-a>window:continue
            between=items[a+1:b]
            counts=collections.Counter(v["op"] for v in between)
            nearby.append({"control":ctl,"distance":b-a,
                           "first_line":va["line"],"last_line":vb["line"],
                           "between":dict(counts),
                           "pair1":list(va["q"][1:]),"pair2":list(vb["q"][1:])})
    nearby.sort(key=lambda t:t["distance"])
    # Cost windows, with separate quantum and classical activity
    scores=[]
    for a in range(0,n,width):
        frag=items[a:min(n,a+width)]
        c=collections.Counter(x["op"] for x in frag)
        quantum_cost=sum(c[k] for k in COST)
        scores.append({"start_index":a,"end_index":min(n,a+width),
                       "start_line":frag[0]["line"],"end_line":frag[-1]["line"],
                       "score":quantum_cost,
                       "CCX":c["CCX"],"CCZ":c["CCZ"],"CSWAP":c["CSWAP"],
                       "HMR":c["HMR"],"BIT_INVERT":c["BIT_INVERT"],
                       "BIT_STORE0":c["BIT_STORE0"],
                       "BIT_STORE1":c["BIT_STORE1"],
                       "conditional_CX":sum(x["op"]=="CX" and x["conditional"] for x in frag),
                       "conditional_CZ":sum(x["op"]=="CZ" and x["conditional"] for x in frag)})
    expensive=sorted(scores,key=lambda x:x["score"],reverse=True)[:top]
    for block in expensive:
        a=block["start_index"]; b=block["end_index"]
        block["excerpt"]=sample_region(items,a,b,excerpt)
    # Every CCZ has symmetric control structure; show relevant correction patterns.
    ccz=[(i,v) for i,v in enumerate(items) if v["op"]=="CCZ"]
    cczsamples=[]
    for i,v in (ccz[:2]+ccz[len(ccz)//2:len(ccz)//2+2]+ccz[-2:]):
        cczsamples.append({"line":v["line"],"q":list(v["q"]),
              "excerpt":sample_region(items,i-9,i+10,excerpt)})
    return {"counts":dict(stats),"total_instructions":n,
            "cswap_controls":controls.most_common(30),
            "cswap_target_pairs":[{"q":list(q),"count":c} for q,c in targetpairs.most_common(20)],
            "cswap_runs":runs[:top],"cswap_run_total":len(runs),
            "cswap_nearby":nearby[:top],
            "expensive_windows":expensive,
            "ccz_samples":cczsamples}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,
       default=ROOT/"competition/k059/results/helios_public.kmx")
    ap.add_argument("--out",type=Path,default=ROOT/"competition/k064/results")
    ap.add_argument("--window",type=int,default=80)
    ap.add_argument("--width",type=int,default=600)
    ap.add_argument("--top",type=int,default=8)
    ap.add_argument("--excerpt",type=int,default=40)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if not args.source.is_file():raise SystemExit("Missing source: "+str(args.source))
    result=investigate(load(args.source),args.width,args.window,args.top,args.excerpt)
    result["source"]=str(args.source)
    result["sha256"]=hashlib.sha256(args.source.read_bytes()).hexdigest()
    result["attribution"]="heliosli public third-party reference"
    out=args.out/"blocks.json"
    out.write_text(json.dumps(result,indent=2))
    print("K064_OVERVIEW",json.dumps({"source_sha256":result["sha256"],
        "counts":{k:result["counts"].get(k,0) for k in
        ("CSWAP","CCX","CCZ","HMR","BIT_INVERT")},
        "cswap_controls":result["cswap_controls"][:12],
        "cswap_run_total":result["cswap_run_total"],
        "top_windows":[{k:w[k] for k in
          ("start_line","end_line","score","CCX","CCZ","CSWAP","HMR")}
          for w in result["expensive_windows"][:5]]},
        sort_keys=True),flush=True)
    for run in result["cswap_runs"][:5]:
        print("K064_CSWAP_RUN",json.dumps(run,sort_keys=True),flush=True)
    for block in result["expensive_windows"][:3]:
        print("K064_HOTSPOT",json.dumps(block,sort_keys=True),flush=True)
    print("K064_SAVED",out,flush=True)

if __name__=="__main__":main()
