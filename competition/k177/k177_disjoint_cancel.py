#!/usr/bin/env python3
"""K177: conservative disjoint-support cancellation on K176 (no baseline overwrite).

Cancel equal unconditional self-inverse gates separated ONLY by unconditional
unitary gates on disjoint qubits. Measurements, conditions, rotations and
unknown operations are hard barriers. Exact commuting identity, not a heuristic.
"""
import argparse, collections, hashlib, json
from pathlib import Path

OPS={"X":1,"Z":1,"CX":2,"CZ":2,"CCX":3,"CCZ":3,"SWAP":2,"CSWAP":3}
SOURCE=Path("competition/k176/results/helios_adjacent_cancel.kmx")
OUT=Path("competition/k177/results/helios_disjoint_cancel.kmx")
REPORT=Path("competition/k177/results/report.json")
SOURCE_SHA="2ca52a953fd989465f23a8699f873e07291662b0cbacb6f0e202d23f34045fb7"

def parse(raw):
    fields=raw.decode("utf8").strip().split()
    if not fields or fields[0] not in OPS or len(fields)!=OPS[fields[0]]+1:
        return None
    if any(not x.startswith("q") or not x[1:].isdigit() for x in fields[1:]):
        return None
    if len(set(fields[1:]))!=len(fields)-1:
        return None
    return (tuple(fields),frozenset(fields[1:]))

def optimize(lines):
    stack=[]
    pairs=[]
    removed=collections.Counter()
    for line_no,raw in enumerate(lines,1):
        gate=parse(raw)
        if gate is None:
            stack.append((raw,None,line_no))
            continue
        key,support=gate
        match=None
        for j in range(len(stack)-1,-1,-1):
            old=stack[j][1]
            if old is None:
                break
            if old[0]==key:
                match=j
                break
            if not support.isdisjoint(old[1]):
                break
        if match is None:
            stack.append((raw,gate,line_no))
        else:
            old_line=stack.pop(match)[2]
            pairs.append((old_line,line_no,key[0]))
            removed[key[0]]+=2
    return b"".join(x[0] for x in stack),pairs,removed

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=SOURCE)
    p.add_argument("--out",type=Path,default=OUT)
    p.add_argument("--report",type=Path,default=REPORT)
    a=p.parse_args()
    original=a.source.read_bytes()
    sha=hashlib.sha256(original).hexdigest()
    if sha!=SOURCE_SHA:
        raise SystemExit("K177_SOURCE_SHA_MISMATCH: "+sha)
    lines=original.splitlines(keepends=True)
    result,pairs,removed=optimize(lines)
    again,second,extra=optimize(result.splitlines(keepends=True))
    assert result==again and not second and not extra, "not at fixed point"
    assert len(lines)-len(result.splitlines())==sum(removed.values())
    # Every deleted pair has identical gates; the stack search guarantees
    # intervening surviving operations have disjoint support.
    for left,right,op in pairs:
        assert parse(lines[left-1])==parse(lines[right-1])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(result)
    report={"source_sha256":sha,"candidate_sha256":hashlib.sha256(result).hexdigest(),
        "source_lines":len(lines),"candidate_lines":len(result.splitlines()),
        "removed":dict(removed),"removed_total":sum(removed.values()),
        "pairs_first_30":pairs[:30],"candidate":str(a.out),
        "official_score":None,"official_pass":None,
        "note":"Only exact disjoint-support involution cancellations. Run official verifier."}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print("K177_RESULT",json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()
