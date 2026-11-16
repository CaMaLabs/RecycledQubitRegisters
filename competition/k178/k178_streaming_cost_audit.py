#!/usr/bin/env python3
"""K178: read-only Helios cost/streaming audit. Never rewrites a circuit.

Reports active qubit lifetimes and repeated expensive controls. Inactivity is
NOT proof that a qubit can be reset/reused: entanglement and coherent state
must be established separately before any width reduction.
"""
import argparse, collections, hashlib, json, re
from pathlib import Path

DEFAULT=Path("competition/k177/results/helios_disjoint_cancel.kmx")
Q=re.compile(r"(?<![A-Za-z0-9_])q(\d+)(?![A-Za-z0-9_])")
COST={"CCX","CCZ","CSWAP"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=DEFAULT)
    p.add_argument("--top",type=int,default=30)
    p.add_argument("--output",type=Path,default=Path("competition/k178/results/audit.json"))
    a=p.parse_args()
    raw=a.source.read_bytes()
    lines=raw.decode("utf8").splitlines()
    first,last={},{}
    touches=collections.Counter()
    gates=collections.Counter()
    costly=[]
    controls=collections.defaultdict(list)
    for n,line in enumerate(lines,1):
        s=line.strip()
        if not s or s.startswith("#"):
            continue
        fields=s.split()
        op=fields[0].upper()
        gates[op]+=1
        ids=tuple(int(x) for x in Q.findall(s))
        for q in set(ids):
            first.setdefault(q,n)
            last[q]=n
            touches[q]+=1
        if op in COST:
            costly.append({"line":n,"op":op,"wires":ids})
            if op in ("CCX","CCZ") and len(ids)==3:
                controls[(op,tuple(sorted(ids[:2])))].append((n,ids[2]))
    wires=sorted(first)
    # Lifetimes are conservative: every qubit considered occupied between
    # first and last use, regardless of idle spans.
    events=collections.Counter()
    for q in wires:
        events[first[q]]+=1
        events[last[q]+1]-=1
    peak=0; active=0
    for n in sorted(events):
        active+=events[n]
        peak=max(peak,active)
    groups=[]
    for (op,ctrl),uses in controls.items():
        if len(uses)>1:
            groups.append({"gate":op,"controls":ctrl,"occurrences":len(uses),
                           "lines_and_targets":uses[:20]})
    groups.sort(key=lambda x:(-x["occurrences"],x["gate"],x["controls"]))
    report={"source":str(a.source),"sha256":hashlib.sha256(raw).hexdigest(),
        "line_count":len(lines),"observed_wires":len(wires),
        "max_wire_index":max(wires,default=None),
        "conservative_live_interval_peak":peak,
        "gate_histogram":dict(gates.most_common()),
        "cost_gate_count":sum(gates[g] for g in COST),
        "repeated_control_groups":groups[:a.top],
        "qubit_lifetimes":[{"wire":q,"first":first[q],"last":last[q],
                            "touches":touches[q]} for q in wires],
        "warning":"No qubit recycling performed. Idle intervals do not imply disentanglement or clean ancillas. Repeated controls do not guarantee profitable sharing."}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n")
    print("K178_AUDIT",json.dumps({k:v for k,v in report.items() if k not in ("qubit_lifetimes","gate_histogram","repeated_control_groups")},sort_keys=True))
    print("K178_GATES",json.dumps(report["gate_histogram"],sort_keys=True))
    print("K178_REPEATED_CONTROLS",json.dumps(groups[:a.top]))
    print("K178_REPORT",a.output)
if __name__=="__main__": main()
