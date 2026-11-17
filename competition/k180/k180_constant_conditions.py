#!/usr/bin/env python3
"""K180: conservative KMX constant-condition elimination.

Only proves constants via BIT_STORE0/1 and BIT_INVERT. Unknown operations,
conditional writes and active unknown condition scopes never justify a deletion.
A PUSH_CONDITION known false removes its complete balanced subtree. Explicit
'if bN' known false removes that instruction. No quantum identities assumed.
"""
import argparse, collections, hashlib, json, re
from pathlib import Path

SOURCE=Path("competition/k177/results/helios_disjoint_cancel.kmx")
OUTPUT=Path("competition/k180/results/helios_const_conditions.kmx")
REPORT=Path("competition/k180/results/report.json")
EXPECTED_SHA="84935736fe1492518e99aa5485ac9fb73418b94f7c056c9c0a69e59b32d9c573"
STORE=re.compile(r"^BIT_STORE([01]) (b\d+)$")
INVERT=re.compile(r"^BIT_INVERT (b\d+)(?: if (b\d+))?$")
PUSH=re.compile(r"^PUSH_CONDITION if (b\d+)$")
COND=re.compile(r"^(.*?) if (b\d+)$")
BIT_TOKEN=re.compile(r"\bb\d+\b")
def rewrite(lines):
    state={}
    stack=[]  # True, False, or None (unknown) for each enclosing condition
    out=[]; removed=collections.Counter(); examples=[]
    def note(n,s,reason):
        removed[reason]+=1
        if len(examples)<25: examples.append({"line":n,"reason":reason,"text":s})
    for n,raw in enumerate(lines,1):
        s=raw.strip()
        if s=="POP_CONDITION":
            if not stack: raise ValueError(f"POP underflow at {n}")
            was_false=False in stack
            stack.pop()
            if was_false: note(n,s,"false_scope")
            else: out.append(raw)
            continue
        push=PUSH.fullmatch(s)
        if push:
            parent_false=False in stack
            value=state.get(push.group(1))
            stack.append(False if parent_false or value==0 else True if value==1 else None)
            if False in stack: note(n,s,"false_scope")
            else: out.append(raw)
            continue
        if False in stack:
            note(n,s,"false_scope")
            continue
        m=COND.fullmatch(s)
        inline=m.group(2) if m else None
        # A false inline guard makes the entire instruction dead.
        if inline is not None and state.get(inline)==0:
            note(n,s,"false_inline")
            continue
        # If any active scope is unknown, instruction may or may not execute.
        unconditional=all(x is True for x in stack) and (inline is None or state.get(inline)==1)
        if (m:=STORE.fullmatch(s)):
            state[m.group(2)]=int(m.group(1)) if unconditional else None
        elif (m:=INVERT.fullmatch(s)):
            bit,guard=m.groups()
            if unconditional and (guard is None or state.get(guard)==1):
                val=state.get(bit)
                state[bit]=1-val if val is not None else None
            elif guard is None or state.get(guard) is not None:
                # A conditional invert with unknown execution can change the bit.
                if guard is None or state.get(guard)!=0: state[bit]=None
            else: state[bit]=None
        else:
            # Unknown operations writing a bit are not interpreted as pure.
            # Conservatively invalidate the first bit operand for BIT_* opcodes.
            fields=s.split()
            if fields and fields[0].startswith("BIT_") and len(fields)>1 and BIT_TOKEN.fullmatch(fields[1]):
                state[fields[1]]=None
        out.append(raw)
    if stack: raise ValueError(f"Unclosed condition scopes: {len(stack)}")
    return out,dict(removed),examples

def selftest():
    src=["BIT_STORE0 b1","CZ q0 q1 if b1","PUSH_CONDITION if b1",
         "CCZ q0 q1 q2","PUSH_CONDITION if b2","X q0",
         "POP_CONDITION","POP_CONDITION","BIT_STORE1 b3",
         "BIT_INVERT b3 if b1","CCX q0 q1 q2 if b3"]
    got,counts,_=rewrite(src)
    assert got==[src[0],src[8],src[10]],(got,counts)
    src=["BIT_STORE0 b1","PUSH_CONDITION if b2","BIT_STORE1 b1",
         "POP_CONDITION","CCZ q0 q1 q2 if b1"]
    got,_,_=rewrite(src)
    assert got==src,got
    print("K180_SELFTEST PASS")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=SOURCE)
    p.add_argument("--output",type=Path,default=OUTPUT)
    p.add_argument("--report",type=Path,default=REPORT)
    p.add_argument("--allow-other-source",action="store_true")
    p.add_argument("--selftest",action="store_true")
    args=p.parse_args()
    selftest()
    if args.selftest:return
    data=args.source.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if not args.allow_other_source and digest!=EXPECTED_SHA:
        raise SystemExit(f"Source SHA mismatch: {digest} != {EXPECTED_SHA}")
    original=data.decode().splitlines(keepends=True)
    result,removed,examples=rewrite(original)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes("".join(result).encode())
    summary={"source_sha256":digest,"candidate_sha256":hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "source_lines":len(original),"candidate_lines":len(result),
        "removed_total":len(original)-len(result),"removed":removed,"examples":examples,
        "caution":"No score improvement claimed; official verifier required."}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(summary,indent=2)+"\n")
    print("K180_RESULT",json.dumps(summary,sort_keys=True))
if __name__=="__main__":main()
