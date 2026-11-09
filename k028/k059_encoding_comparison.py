#!/usr/bin/env python3
"""K059: compare human-readable Kickmix gate encoding of public and own circuits."""
from __future__ import annotations
from pathlib import Path
from collections import Counter,deque
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
import kickmix as km
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inspect(p):
    counts=Counter();pairs=Counter();prev=None;examples={}
    with p.open(errors="replace") as f:
        for line in f:
            line=line.split("#",1)[0].strip()
            if not line or line.startswith("//"):continue
            op=line.split()[0].upper()
            if not re.fullmatch("[A-Z_][A-Z_0-9]*",op):continue
            counts[op]+=1
            if len(examples.get(op,[]))<2:examples.setdefault(op,[]).append(line[:200])
            if prev:pairs[prev+" -> "+op]+=1
            prev=op
    return {"opcodes":dict(counts.most_common()),
            "pairs":dict(pairs.most_common(30)),"examples":examples}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=ROOT/"competition/k059/results")
    p.add_argument("--include-k056",action="store_true")
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    paths={"helios_public":ROOT/"competition/k058/results/dataset/invsqrt.kmb",
           "k040_ours":ROOT/"competition/k040/results/recycle.kmb"}
    if a.include_k056:paths["k056_ours"]=ROOT/"competition/k056/results/fixed_point_horner_bounded.kmb"
    results={}
    for label,src in paths.items():
        if not src.is_file():
            results[label]={"status":"MISSING","path":str(src)}
            print("K059_MISSING",str(src),flush=True)
            continue
        try:
            circuit=km.Circuit.from_file(str(src),format="kmb")
            kmx=a.out/(label+".kmx")
            circuit.to_file(str(kmx),format="kmx")
            facts=inspect(kmx)
            facts.update({"status":"OK","qubits":circuit.num_qubits,
                          "kmb_sha256":sha(src),"kmx_sha256":sha(kmx),
                          "kmx_path":str(kmx),"kmx_bytes":kmx.stat().st_size})
            results[label]=facts
            print("K059_CIRCUIT",json.dumps({
                "label":label,"qubits":circuit.num_qubits,
                "opcodes":facts["opcodes"],"kmx_bytes":facts["kmx_bytes"]
            },sort_keys=True),flush=True)
        except Exception as exc:
            results[label]={"status":"ERROR","error":repr(exc)}
            print("K059_ERROR",label,repr(exc),flush=True)
    output=a.out/"comparison.json"
    output.write_text(json.dumps({
        "attribution":"heliosli/qcc-circuits-live public circuit is third-party",
        "note":"Gate-level encoding analysis only; no full-domain candidate created",
        "circuits":results},indent=2))
    print("K059_RESULT",json.dumps({k:v["status"] for k,v in results.items()}),flush=True)
    print("SAVED",str(output),flush=True)
if __name__=="__main__":main()
