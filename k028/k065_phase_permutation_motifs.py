#!/usr/bin/env python3
"""K065: analyze Helios invsqrt's controlled-permutation and phase-scan motifs.

Read-only reverse-engineering of a third-party public benchmark.
Distinguish observed gate structure from hypotheses; do not claim that a
different circuit is valid without formal equivalence and official verification.
"""
from __future__ import annotations
import argparse, collections, decimal, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
Q=re.compile(r"\bq(\d+)\b")
D=decimal.Decimal
decimal.getcontext().prec=70
def load(path):
    data=[]
    for line_no,raw in enumerate(path.read_text().splitlines(),1):
        s=raw.strip()
        if not s:continue
        parts=s.split()
        op=parts[0].upper()
        qs=tuple(int(x) for x in Q.findall(s))
        angle=None
        if op=="Z_POW" and len(parts)>=3:
            try:angle=D(parts[2])
            except decimal.InvalidOperation:pass
        data.append({"line":line_no,"op":op,"qs":qs,"angle":angle,
                     "conditional":" if b" in s,"text":s})
    return data
def cswap_runs(data):
    runs=[]
    i=0
    while i<len(data):
        x=data[i]
        if x["op"]!="CSWAP" or len(x["qs"])!=3:
            i+=1;continue
        ctl=x["qs"][0]
        j=i+1
        while j<len(data) and data[j]["op"]=="CSWAP" and len(data[j]["qs"])==3 and data[j]["qs"][0]==ctl:j+=1
        seq=data[i:j]
        if len(seq)>=2:
            pairs=[list(g["qs"][1:]) for g in seq]
            const_sums=[sum(p) for p in pairs]
            first=[p[0] for p in pairs];second=[p[1] for p in pairs]
            reverse=(len(set(const_sums))==1 and
                     all(b-a==1 for a,b in zip(first,first[1:])) and
                     all(b-a==-1 for a,b in zip(second,second[1:])))
            runs.append({"control":ctl,"count":len(seq),"lines":[seq[0]["line"],seq[-1]["line"]],
                         "pair_sum":const_sums[0] if reverse else None,
                         "reverse_mirror":reverse,"pairs":pairs})
        i=j
    return runs
def phase_ladders(data,min_length):
    # Group nearby Z_POW events into chains whenever consecutive occurrences
    # are separated by at most 24 instructions. Other gates ARE included.
    events=[(i,x) for i,x in enumerate(data) if x["op"]=="Z_POW" and x["angle"] is not None]
    clusters=[]
    current=[]
    for i,x in events:
        if current and i-current[-1][0]>24:
            if len(current)>=min_length:clusters.append(current)
            current=[]
        current.append((i,x))
    if len(current)>=min_length:clusters.append(current)
    results=[]
    for c in clusters:
        angles=[v["angle"] for _,v in c]
        ratios=[]
        for a,b in zip(angles,angles[1:]):
            ratios.append(str(b/a) if a else None)
        start=max(0,c[0][0]-6);end=min(len(data),c[-1][0]+7)
        ops=collections.Counter(x["op"] for x in data[start:end])
        results.append({"count":len(c),"lines":[c[0][1]["line"],c[-1][1]["line"]],
                        "qubits":[x["qs"][0] for _,x in c],
                        "angles":[str(a) for a in angles],
                        "ratios":ratios,
                        "nearby_opcounts":dict(ops),
                        "first_surroundings":[x["text"] for x in data[max(0,c[0][0]-6):c[0][0]+8]],
                        "last_surroundings":[x["text"] for x in data[max(0,c[-1][0]-6):min(len(data),c[-1][0]+8)]]})
    return sorted(results,key=lambda r:r["count"],reverse=True)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,default=ROOT/"competition/k059/results/helios_public.kmx")
    ap.add_argument("--out",type=Path,default=ROOT/"competition/k065/results")
    ap.add_argument("--min-phase-length",type=int,default=3)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    if not a.source.is_file():raise SystemExit("No decoded KMX: "+str(a.source))
    data=load(a.source)
    runs=cswap_runs(data)
    ladders=phase_ladders(data,a.min_phase_length)
    qcost=collections.Counter(x["op"] for x in data)
    report={"source":str(a.source),"sha256":hashlib.sha256(a.source.read_bytes()).hexdigest(),
            "attribution":"Helios public third-party circuit; read-only analysis",
            "swap_runs":runs,"phase_ladders":ladders,
            "total_symmetric_reverse_swaps":sum(r["count"] for r in runs if r["reverse_mirror"]),
            "total_swap_in_runs":sum(r["count"] for r in runs),
            "baseline_cost":{"CCX":qcost["CCX"],"CSWAP":qcost["CSWAP"],"CCZ":qcost["CCZ"]},
            "warning":"No inference of semantic equivalence or gate savings from a motif alone"}
    p=a.out/"motifs.json";p.write_text(json.dumps(report,indent=2))
    print("K065_OVERVIEW",json.dumps({"cswap_runs":len(runs),
          "symmetric_reverse_swaps":report["total_symmetric_reverse_swaps"],
          "swaps_in_runs":report["total_swap_in_runs"],
          "phase_ladders":len(ladders),"baseline":report["baseline_cost"]},sort_keys=True),flush=True)
    for r in runs[:10]:print("K065_SWAP_RUN",json.dumps(r,sort_keys=True),flush=True)
    for r in ladders[:6]:print("K065_PHASE_LADDER",json.dumps(r,sort_keys=True),flush=True)
    print("K065_SAVED",str(p),flush=True)
if __name__=="__main__":main()
