#!/usr/bin/env python3
"""A16: Pareto compare compiled placement metrics from A13 and A15 receipts.
Read-only offline analysis, no QPU, no modifications to circuit or postprocessor.
Missing reset calibrations stay explicitly unknown; no estimated physical BER.
"""
import argparse,json,math
from pathlib import Path

METRICS=("cz","depth","measure_mean","log_risk_proxy")
def dominate(a,b,keys):
    return all(a[k]<=b[k] for k in keys) and any(a[k]<b[k] for k in keys)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--a13",default="results/qrr_a13_fez_branch_calibration.json")
    p.add_argument("--a15",default="results/qrr_a15_fez_measure_reset_calibration.json")
    p.add_argument("--output",default="results/qrr_a16_placement_pareto.json")
    args=p.parse_args()
    d13=json.loads(Path(args.a13).read_text());d15=json.loads(Path(args.a15).read_text())
    assert d13["status"]=="COMPLETE_BRANCH_AWARE_PROXY_ONLY"
    assert d15["status"]=="COMPLETE_CALIBRATION_METADATA_ONLY"
    lookup={(r["base"],r["bits"]):r for r in d13["rows"]}
    report={"status":"STARTED","metrics":list(METRICS),"qpu_jobs":0,
      "interpretation":"Pareto of measurements, compiled CZ/depth and unweighted-all-branches log-risk proxy; NOT measured shot fidelity or BER",
      "reset_calibration_known":False,"rows":[]}
    for r in d15["rows"]:
        key=(r["base"],r["bits"])
        assert key in lookup
        native={s["seed"]:s for s in lookup[key]["seeds"]}
        placements=[]
        for s in r["seeds"]:
            a=native[s["seed"]]
            assert int(a["cz_top_level"])==int(s["native_cz"])
            assert int(a["depth"])==int(s["native_depth"])
            val=s["measure"]["mean_calibrated_error"]
            if val is None:raise AssertionError("missing measurement error data: cannot compare")
            placements.append({"seed":s["seed"],"cz":int(s["native_cz"]),
              "depth":int(s["native_depth"]),"measure_mean":float(val),
              "log_risk_proxy":float(a["details"]["naive_all_branches_log_risk_upper_proxy"]),
              "reset_known":s["reset"]["mean_calibrated_error"] is not None,
              "measure_locations":s["measure"]["physical_qubits"]})
        frontier=[s["seed"] for s in placements if not any(
          dominate(t,s,METRICS) for t in placements if t["seed"]!=s["seed"])]
        # Report individual minima; absent calibrated reset error must not be made up.
        minima={k:min(placements,key=lambda x:x[k])["seed"] for k in METRICS}
        report["rows"].append({"base":key[0],"bits":key[1],
          "pareto_seed_ids":frontier,"individual_minima":minima,
          "placements":placements,"reset_calibration_complete":all(x["reset_known"] for x in placements)})
        print("A16",*key,"Pareto",frontier,"minima",minima,flush=True)
    assert len(report["rows"])==6
    assert not any(r["reset_calibration_complete"] for r in report["rows"])
    report["status"]="PASS_PARTIAL_CALIBRATION"
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"qpu_jobs":0,
        "pareto":[{"base":r["base"],"bits":r["bits"],"seeds":r["pareto_seed_ids"]} for r in report["rows"]]},indent=2))
if __name__=="__main__":main()
