#!/usr/bin/env python3
"""Zero-QPU topology-only Fez-vs-Nighthawk benchmark for recycled QPE.

Both sides use the same GenericBackendV2 basis/dynamic-circuit settings; only
connectivity changes.  Fez connectivity is read from ibm_fez.  The script tries
to read ibm_phoenix metadata; if unavailable it uses a clearly labeled 10x12,
120-qubit square-lattice proxy consistent with IBM's public Nighthawk description.
No QPU job is submitted.  This is a topology/compiler proxy, not a calibrated
Phoenix performance prediction.
"""
from __future__ import annotations

import argparse, json, statistics
from datetime import datetime, timezone
from pathlib import Path
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap
import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

REV = "2026-09-15-fez-vs-nighthawk-topology-v1"
OUT = Path("results/qubit_recycling/ibm_fez_vs_nighthawk_topology_recycling.json")
BASIS = ["rz", "sx", "x", "cz"]


def backend_coupling(backend):
    try:
        cm = backend.target.build_coupling_map()
    except Exception:
        cm = None
    if cm is None:
        cm = backend.coupling_map
    return cm if isinstance(cm, CouplingMap) else CouplingMap(cm)


def symmetric(cm, n):
    pairs = {tuple(sorted((int(u), int(v)))) for u, v in cm.get_edges() if u != v}
    out = CouplingMap([[x, y] for a, b in sorted(pairs) for x, y in ((a, b), (b, a))])
    while out.size() < n:
        out.graph.add_node(None)
    if out.size() != n:
        raise RuntimeError(f"coupling width {out.size()} != {n}")
    return out


def topo_stats(cm):
    n = cm.size(); ns = [set() for _ in range(n)]
    for u, v in cm.get_edges():
        if u != v:
            ns[int(u)].add(int(v)); ns[int(v)].add(int(u))
    d = [len(x) for x in ns]
    return {"num_qubits": n, "undirected_edges": sum(d)//2,
            "degree_min": min(d), "degree_mean": statistics.fmean(d),
            "degree_max": max(d),
            "degree_histogram": {str(k): sum(x == k for x in d) for k in sorted(set(d))}}


def generic(n, cm):
    return GenericBackendV2(num_qubits=n, basis_gates=BASIS, coupling_map=cm,
                            control_flow=True, seed=8776, noise_info=False)


def nighthawk_map(service):
    try:
        b = service.backend("ibm_phoenix")
        cm = symmetric(backend_coupling(b), int(b.num_qubits))
        return cm, {"mode": "authenticated_ibm_phoenix_coupling_metadata",
                    "backend_name": str(b.name), "proxy": False,
                    "note": "Connectivity only; edge directions symmetrized and calibration discarded."}
    except Exception as exc:
        cm = CouplingMap.from_grid(10, 12, bidirectional=True)
        return cm, {"mode": "public_nighthawk_square_lattice_proxy_10x12",
                    "backend_name": None, "proxy": True,
                    "metadata_lookup_error_type": type(exc).__name__,
                    "metadata_lookup_error": str(exc),
                    "note": "Proxy only. IBM documents 120 programmable qubits and a square lattice with most qubits degree four; 10x12 is not asserted to be Phoenix's exact edge map."}


def compact(r):
    if r is None: return None
    ks = ("topology","kind","phase_bits","logical_qubits","compiled_touched_qubits",
          "extra_physical_qubits_borrowed","strict_width_pass","seed_transpiler",
          "native_cz","compiled_depth","compiled_size","compile_seconds")
    return {k: r.get(k) for k in ks}


def best(rows, topology, kind, bits):
    s = [r for r in rows if r.get("success") and r.get("strict_width_pass")
         and r["topology"] == topology and r["kind"] == kind and r["phase_bits"] == bits]
    return min(s, key=lambda r:(r["native_cz"],r["compiled_depth"],r["seed_transpiler"])) if s else None


def div(a,b): return None if not b else float(a/b)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--fez-backend",default="ibm_fez")
    ap.add_argument("--phase-bits",nargs="+",type=int,default=[4,8,12,16,20])
    ap.add_argument("--scratch-bits",type=int,default=1)
    ap.add_argument("--profile",default="auto")
    ap.add_argument("--optimization-level",type=int,choices=[0,1,2,3],default=3)
    ap.add_argument("--seeds",default="8776,2026,9401")
    ap.add_argument("--out",type=Path,default=OUT)
    a=ap.parse_args(); bits=sorted(set(a.phase_bits)); seeds=[int(x) for x in a.seeds.split(",") if x]
    if not bits or min(bits)<1 or a.scratch_bits<0 or not seeds: raise SystemExit("invalid arguments")

    service=width.ref.ibm_base.make_service()
    fez=width.ref.ibm_base.select_backend(service,direct.WORK_BITS+max(bits)+a.scratch_bits,a.fez_backend)
    fcm=symmetric(backend_coupling(fez),int(fez.num_qubits))
    ncm,nsrc=nighthawk_map(service)
    if direct.WORK_BITS+max(bits)+a.scratch_bits > ncm.size():
        raise SystemExit("requested wide precision exceeds Nighthawk width")
    backends={"fez_heavy_hex_topology":generic(fcm.size(),fcm),
              "nighthawk_square_lattice_topology":generic(ncm.size(),ncm)}
    meta={"fez_heavy_hex_topology":{"source":"authenticated_ibm_fez_coupling_metadata","backend_name":str(fez.name),**topo_stats(fcm)},
          "nighthawk_square_lattice_topology":{"source":nsrc,**topo_stats(ncm)}}

    print("ZERO-QPU TOPOLOGY BENCHMARK: no Sampler or QPU job is used.")
    print(f"Fez={fez.name} Nighthawk_source={nsrc['mode']} common_basis={BASIS}")
    if nsrc["proxy"]: print("IMPORTANT: Nighthawk side is a 10x12 square-lattice PROXY, not exact Phoenix.")

    res={"experiment":"ibm_fez_vs_nighthawk_topology_recycling_v1","script_revision":REV,
         "timestamp_utc":datetime.now(timezone.utc).isoformat(),"zero_qpu":True,"qpu_jobs_submitted":0,
         "N":direct.N,"base":direct.A,"work_bits":direct.WORK_BITS,"scratch_bits":a.scratch_bits,
         "phase_bits":bits,"profile":a.profile,"optimization_level":a.optimization_level,"seeds":seeds,
         "common_basis":BASIS,"control_flow_enabled":True,"topologies":meta,
         "order_used_in_circuit_construction":False,"orbit_encoding_used":False,
         "strict_width_definition":"compiled_touched_qubits <= source logical_qubits",
         "scope_boundary":"Topology-only compiler proxy; normalized basis, no calibration/timing/reset-speed/fidelity. N=35 remains exact small-N full-register synthesis, not scalable RSA arithmetic.","rows":[]}

    for m in bits:
        if not direct.semantic_summary(m)["pass"]: raise RuntimeError(f"semantic failure at {m}")
        for kind in ("recycled","wide"):
            qc,rounds,_=width.build(kind,m,a.scratch_bits,use_measure2=False)
            logical=qc.num_qubits; mcx=sum(int(r.get("direct_mcx",0)) for r in rounds)
            print(f"\n===== bits={m} kind={kind} allocated={logical}q direct_mcx={mcx} =====")
            for tn,b in backends.items():
                for seed in seeds:
                    print(f"compile topology={tn} seed={seed}")
                    try:
                        st=width.compile_one(qc,b,a.profile,a.optimization_level,seed); touched=int(st["compiled_touched_qubits"])
                        row={"success":True,"topology":tn,"kind":kind,"phase_bits":m,"logical_qubits":logical,
                             "seed_transpiler":seed,"semantic_pass":True,"total_direct_mcx":mcx,
                             "compiled_touched_qubits":touched,"extra_physical_qubits_borrowed":max(0,touched-logical),
                             "strict_width_pass":touched<=logical,"order_used_in_circuit_construction":False,
                             "orbit_encoding_used":False,**{k:v for k,v in st.items() if k!="compiled_touched_qubits"}}
                        print(f"  -> touched={touched} strict={row['strict_width_pass']} CZ={row['native_cz']} depth={row['compiled_depth']}")
                    except Exception as exc:
                        row={"success":False,"topology":tn,"kind":kind,"phase_bits":m,"logical_qubits":logical,
                             "seed_transpiler":seed,"error_type":type(exc).__name__,"error":str(exc)}
                        print(f"  -> FAIL {type(exc).__name__}: {exc}")
                    res["rows"].append(row); a.out.parent.mkdir(parents=True,exist_ok=True)
                    a.out.write_text(json.dumps(res,indent=2,default=str)+"\n")

    bst={}; cmp={}
    for m in bits:
        k=str(m); bst[k]={tn:{kind:best(res["rows"],tn,kind,m) for kind in ("recycled","wide")} for tn in backends}
        fr,fw=bst[k]["fez_heavy_hex_topology"]["recycled"],bst[k]["fez_heavy_hex_topology"]["wide"]
        nr,nw=bst[k]["nighthawk_square_lattice_topology"]["recycled"],bst[k]["nighthawk_square_lattice_topology"]["wide"]
        if all(x is not None for x in (fr,fw,nr,nw)):
            fcz,ncz=div(fr["native_cz"],fw["native_cz"]),div(nr["native_cz"],nw["native_cz"])
            fd,nd=div(fr["compiled_depth"],fw["compiled_depth"]),div(nr["compiled_depth"],nw["compiled_depth"])
            cmp[k]={"phase_bits":m,"logical_width_recycled":fr["logical_qubits"],"logical_width_wide":fw["logical_qubits"],
                    "logical_qubits_saved":fw["logical_qubits"]-fr["logical_qubits"],
                    "fez_recycled_over_wide_cz_ratio":fcz,"nighthawk_recycled_over_wide_cz_ratio":ncz,
                    "recycling_cz_ratio_nighthawk_over_fez":div(ncz,fcz),
                    "fez_recycled_over_wide_depth_ratio":fd,"nighthawk_recycled_over_wide_depth_ratio":nd,
                    "recycling_depth_ratio_nighthawk_over_fez":div(nd,fd),
                    "recycled_nighthawk_over_fez_cz_ratio":div(nr["native_cz"],fr["native_cz"]),
                    "wide_nighthawk_over_fez_cz_ratio":div(nw["native_cz"],fw["native_cz"])}
    res["best_strict"]=bst; res["comparisons"]=cmp; a.out.write_text(json.dumps(res,indent=2,default=str)+"\n")

    print("\n===== TOPOLOGY METADATA ====="); print(json.dumps(meta,indent=2,default=str))
    print("\n===== TOPOLOGY COMPARISON SUMMARY =====")
    for m in bits:
        c=cmp.get(str(m))
        if not c: print(f"bits={m}: missing strict result"); continue
        print(f"bits={m}: width {c['logical_width_wide']}->{c['logical_width_recycled']} saved={c['logical_qubits_saved']} | "
              f"R/W CZ Fez={c['fez_recycled_over_wide_cz_ratio']:.4f} Nighthawk={c['nighthawk_recycled_over_wide_cz_ratio']:.4f} amp={c['recycling_cz_ratio_nighthawk_over_fez']:.4f} | "
              f"R/W depth Fez={c['fez_recycled_over_wide_depth_ratio']:.4f} Nighthawk={c['nighthawk_recycled_over_wide_depth_ratio']:.4f} amp={c['recycling_depth_ratio_nighthawk_over_fez']:.4f}")
    print("\n===== BEST STRICT ROWS =====")
    for m in bits:
        for tn in backends:
            for kind in ("recycled","wide"):
                print(f"bits={m} topology={tn} kind={kind} {json.dumps(compact(bst[str(m)][tn][kind]),sort_keys=True)}")
    print(f"\nwrote {a.out}\nNO QPU JOB SUBMITTED."); return 0

if __name__ == "__main__": raise SystemExit(main())
