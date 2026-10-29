#!/usr/bin/env python3
"""N35/N209 and all fresh N27 public-identity controlled-modmul source cost audit.

Public factor/order-independent multiplier==1 optimization only; no hardware.
"""
import json, math, hashlib
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from hardware import dark_star_recycled_scalable_arithmetic_audit as g

ROOT=Path("results/dark_star_unified")
MAN=ROOT/"unified_n27_restored_public_manifest.json"
DEST=ROOT/"unified_n27_public_identity_U_source_audit.json"
SHA="12f169a7edabe5d548dba4c8bd07d348a2bd174378ad2faf934dcfe8b5828b10"
MS=(4,8,16,32,54)

def exhaustive_small_controlled_identity():
    tested=0
    for n in (15,21,35,77,209):
        for x in range(n):
            for control in (0,1):
                original=x if control==0 else (x*1)%n
                pruned=x
                assert original==pruned
                tested+=1
    return tested

def row(n,a,m,tag,cache):
    assert 1<a<n and math.gcd(n,a)==1
    identity=g.public_identity_rounds(n,a,m)
    old=g.stage_arithmetic_count(n,a,m,cache)
    fixed=g.stage_arithmetic_count_public_identity_pruned(n,a,m,cache)
    delta={k:int(old.get(k,0)-fixed.get(k,0)) for k in ("ccx","cx","cswap")}
    assert all(v>=0 for v in delta.values())
    expected=Counter()
    multipliers=[]
    multiplier=a%n
    for k in range(m):
        multipliers.append(multiplier)
        if multiplier==1:
            expected.update(g.controlled_modmul_count(n,1))
        multiplier=(multiplier*multiplier)%n
    for gate in ("ccx","cx","cswap"):
        assert delta[gate]==expected.get(gate,0)
    assert [k for k,z in enumerate(multipliers) if z==1]==identity
    assert (delta["ccx"]>0)==(len(identity)>0)
    return dict(tag=tag,N=n,base=a,phase_bits=m,
        public_multipliers=multipliers,public_identity_rounds=identity,
        identity_round_count=len(identity),
        unpruned_source_counts={k:int(old.get(k,0)) for k in ("ccx","cx","cswap")},
        source_counts_after_safe_public_identity_elision={k:int(fixed.get(k,0)) for k in ("ccx","cx","cswap")},
        exact_saved_counts=delta,
        source_CCX_relative_saving=(delta["ccx"]/old["ccx"] if old["ccx"] else None),
        no_secret_order_or_factors_in_source_construction=True,
        arithmetic_logical_peak_width_unchanged=g.arithmetic_width(n)["recycled_logical_qubits"],
        no_native_device_gate_or_depth_benchmark=True)

def main():
    m=json.loads(MAN.read_text())
    rr=m["selected_public_rows"]
    assert m["selected_sha256"]==SHA and len(rr)==12
    assert m["no_private_pq_or_order_in_ranking_or_base_selection"] and m["zero_QPU"]
    anchors=[(35,2,(4,6,8,12)),(35,8,(4,6,8,12)),
             (209,3,(4,6,8,16)),(209,27,(4,6,8,16)),
             (713,19,(4,6,8,16)),(713,pow(19,3,713),(4,6,8,16)),
             (15,4,(4,6,8,16)),(21,8,(4,6,8,16))]
    out=[]
    cache={}
    for n,a,bits in anchors:
        for bit in bits:
            out.append(row(n,a,bit,"frozen_small_anchor",cache))
    for f in rr:
        for base,tag in ((f["base"],"new_N27_plain"),(f["public_cube"],"new_N27_cube")):
            for bit in MS:
                out.append(row(f["N"],base,bit,tag,cache))
    assert len(out)==len(anchors)*4+12*2*len(MS)
    anchor=next(x for x in out if x["N"]==35 and x["base"]==8 and x["phase_bits"]==4)
    assert anchor["public_identity_rounds"]==[2,3] and anchor["exact_saved_counts"]["ccx"]>0
    same=exhaustive_small_controlled_identity()
    assert same>600
    by_tag={}
    for label in sorted({x["tag"] for x in out}):
        z=[x for x in out if x["tag"]==label]
        ccx=sum(x["unpruned_source_counts"]["ccx"] for x in z)
        saved=sum(x["exact_saved_counts"]["ccx"] for x in z)
        by_tag[label]=dict(rows=len(z),rows_with_nonzero_source_savings=sum(x["exact_saved_counts"]["ccx"]>0 for x in z),
            all_public_identity_rounds=sum(x["identity_round_count"] for x in z),
            baseline_source_CCX=ccx,exact_identity_source_CCX_saved=saved,
            identity_source_CCX_fraction=saved/ccx if ccx else None)
    result=dict(experiment="Dark_Star_N27_public_multiplier_identity_U_pruning",
        preregistration="docs/DARK_STAR_N27_RESTORED_PLUS_IDENTITY_PRUNING_PREREG.md",
        original_public_n27_sha=SHA,complete=True,
        formula="skip only U_(a^(2^k) mod N) when publicly equal 1; controlled I is identity; other U unchanged",
        reference_case_N35_cube_identity_rounds=[2,3],
        exhaustive_small_semantic_controls=tested if False else same,
        group_summary=by_tag,all_raw_cases=out,
        physical_native_CZ_or_depth_measured=False,
        no_private_order_or_factors_used_for_gate_selection=True,
        zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False,
        conclusion_caveat="structural CCX/CX/CSWAP only; no compiled native CZ/depth/fidelity or device runtime savings asserted. N35 scratch 32->23 separate failed robust native benefit.",
        analyzed_utc=datetime.now(timezone.utc).isoformat())
    DEST.write_text(json.dumps(result,indent=2)+"\n")
    print("COMPLETE independent source prune audit",json.dumps(by_tag),"exhaustive",same,"NO QPU",flush=True)

if __name__=="__main__":
    main()
