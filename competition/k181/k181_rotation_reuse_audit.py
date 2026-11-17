#!/usr/bin/env python3
"""K181: rotation and coherent-register-reuse reconnaissance.

Read-only. No approximation or qubit reuse is asserted safe. Produces a compact
machine-readable list of rotation sites and potential reset/measurement markers.
"""
import argparse, collections, hashlib, json, re
from pathlib import Path
SRC=Path("competition/k180/results/helios_const_conditions.kmx")
OUT=Path("competition/k181/results/audit.json")
Q=re.compile(r"\bq\d+\b")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,default=SRC)
    ap.add_argument("--output",type=Path,default=OUT)
    ap.add_argument("--window",type=int,default=4)
    args=ap.parse_args()
    data=args.source.read_bytes()
    lines=data.decode().splitlines()
    stack=[]; rotations=[]; resets=[]; measurements=[]; opcounts=collections.Counter()
    for i,s in enumerate(lines,1):
        tok=s.split()
        if not tok:continue
        op=tok[0];opcounts[op]+=1
        if op=="PUSH_CONDITION":
            stack.append(" ".join(tok[1:]))
        elif op=="POP_CONDITION":
            if not stack:raise ValueError(f"condition stack underflow line {i}")
            stack.pop()
        # ROTATION ops only: no assumption that every HMR is a rotation.
        if any(t in op.upper() for t in ("ROT","RZ","RX","RY","PHASE","ANGLE")):
            rotations.append({"line":i,"instruction":s,"conditions":stack.copy(),
              "context":[{"line":j+1,"instruction":lines[j]} for j in range(max(0,i-1-args.window),min(len(lines),i+args.window))]})
        if any(t in op.upper() for t in ("RESET","INIT","PREPARE")):
            resets.append({"line":i,"instruction":s,"conditions":stack.copy()})
        if any(t in op.upper() for t in ("MEASURE","HMR","MZ","MX")):
            measurements.append({"line":i,"instruction":s,"conditions":stack.copy()})
    if stack:raise ValueError(f"unclosed condition scopes: {len(stack)}")
    r={"source":str(args.source),"sha256":hashlib.sha256(data).hexdigest(),
      "lines":len(lines),"opcodes":dict(opcounts.most_common()),
      "rotation_like_instructions":rotations,
      "initialization_or_reset_markers":resets,
      "measurement_like_count":len(measurements),
      "measurement_like_sample":measurements[:50],
      "cautions":["A measurement does not imply a reusable qubit.",
      "A reset is not safe when its pre-reset state is still entangled or required.",
      "Verifier rotation_count may count synthesized or implicit rotations not visible as rotation opcodes.",
      "No gate substitution or error-sensitivity measurement performed."]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2)+"\n")
    print("K181_SUMMARY",json.dumps({"source_sha256":r["sha256"],
      "rotation_like_count":len(rotations),"reset_marker_count":len(resets),
      "measurement_like_count":len(measurements),
      "opcodes":r["opcodes"]},sort_keys=True))
    print("K181_ROTATION_SITES",json.dumps([{"line":x["line"],"instruction":x["instruction"],"conditions":x["conditions"]} for x in rotations]))
    print("K181_RESET_MARKERS",json.dumps(resets[:30]))
    print("K181_REPORT",args.output)
if __name__=="__main__":main()
